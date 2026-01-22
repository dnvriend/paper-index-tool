"""Vector search using FAISS and Bedrock embeddings.

This module provides semantic search capabilities using AWS Bedrock
embeddings and FAISS vector index. It enables natural language queries
that match on meaning rather than keywords.

Classes:
    VectorSearcher: Semantic search across papers, books, and media.

The VectorSearcher follows the same interface as BM25 searchers but
uses embedding-based similarity instead of keyword matching.
"""

from __future__ import annotations

import json
from typing import Any

from paper_index_tool.logging_config import get_logger
from paper_index_tool.models import Book, Media, Paper
from paper_index_tool.search import EntryType, SearchResult, extract_fragments
from paper_index_tool.storage import (
    BookRegistry,
    MediaRegistry,
    PaperRegistry,
    get_chunks_path,
    get_faiss_index_path,
    get_named_index_chunks_path,
    get_named_index_faiss_path,
    get_vector_index_dir,
)
from paper_index_tool.vector.chunking import CharacterLimitChunker, Chunk, TextChunker
from paper_index_tool.vector.embeddings import BedrockEmbeddings
from paper_index_tool.vector.errors import IndexNotFoundError, NamedIndexNotFoundError

logger = get_logger(__name__)


class VectorSearcher:
    """Semantic search using FAISS and Bedrock embeddings.

    Provides semantic search capabilities across papers, books, and media.
    Uses AWS Bedrock embedding models and FAISS for vector similarity.

    Unlike BM25 search which matches keywords, semantic search matches
    on meaning - enabling natural language queries like questions.

    Supports multiple named indices with different embedding models.

    Attributes:
        embeddings: BedrockEmbeddings client.
        chunker: TextChunker for splitting documents.
        paper_registry: Registry for papers.
        book_registry: Registry for books.
        media_registry: Registry for media.
        index_name: Name of the active index (None for legacy).

    Example:
        >>> searcher = VectorSearcher(index_name="nova-1024")
        >>> searcher.rebuild_index()
        >>> results = searcher.search("How do leaders develop?", top_k=5)
        >>> for r in results:
        ...     print(f"{r.entry_id}: {r.score:.2f}")
    """

    def __init__(
        self,
        index_name: str | None = None,
        model_name: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        """Initialize vector searcher.

        Creates embeddings client, chunker, and registry instances.
        Does not load the FAISS index until needed.

        Args:
            index_name: Named index to use (None for legacy single index).
            model_name: Embedding model for queries. Required for named indices
                        if not specified, will be loaded from index metadata.
            dimensions: Embedding dimensions. Required for named indices
                        if not specified, will be loaded from index metadata.
        """
        self.index_name = index_name
        self._model_name = model_name
        self._dimensions = dimensions

        # Defer embeddings creation until we know the model
        self._embeddings: BedrockEmbeddings | None = None

        self.chunker = TextChunker()
        self._char_limit_chunker: CharacterLimitChunker | None = None
        self.paper_registry = PaperRegistry()
        self.book_registry = BookRegistry()
        self.media_registry = MediaRegistry()
        self._index: Any = None  # FAISS index
        self._chunks: list[Chunk] = []

    def _get_char_limit_chunker(self) -> CharacterLimitChunker:
        """Get character limit chunker based on embedding model.

        Creates a CharacterLimitChunker with max_chars derived from
        the embedding model's max_input_tokens (~4.7 chars per token).

        Returns:
            CharacterLimitChunker configured for the current model.
        """
        if self._char_limit_chunker is not None:
            return self._char_limit_chunker

        # Get model's max tokens and calculate max chars
        model_config = self.embeddings.config
        max_chars = int(model_config.max_input_tokens * 4.7)

        self._char_limit_chunker = CharacterLimitChunker(max_chars=max_chars)
        logger.debug(
            "Created CharacterLimitChunker with max_chars=%d (model: %s, max_tokens=%d)",
            max_chars,
            self.embeddings.model_name,
            model_config.max_input_tokens,
        )
        return self._char_limit_chunker

    @property
    def embeddings(self) -> BedrockEmbeddings:
        """Get or create embeddings client.

        For named indices, loads model config from index metadata.
        """
        if self._embeddings is not None:
            return self._embeddings

        if self.index_name:
            # Load model from index metadata
            from paper_index_tool.vector.registry import VectorIndexRegistry

            registry = VectorIndexRegistry()
            try:
                metadata = registry.get_index(self.index_name)
                model_name = registry.get_model_name_for_index(self.index_name)
                self._embeddings = BedrockEmbeddings(
                    model_name=model_name,
                    dimensions=metadata.dimensions,
                )
            except NamedIndexNotFoundError:
                # Index doesn't exist yet, use provided or default model
                if self._model_name:
                    self._embeddings = BedrockEmbeddings(
                        model_name=self._model_name,
                        dimensions=self._dimensions,
                    )
                else:
                    # Default to titan-v2
                    self._embeddings = BedrockEmbeddings()
        else:
            # Legacy mode - use default model
            self._embeddings = BedrockEmbeddings(
                model_name=self._model_name or "titan-v2",
                dimensions=self._dimensions,
            )

        return self._embeddings

    def _get_faiss(self) -> Any:
        """Import and return faiss module.

        Returns:
            The faiss module.

        Raises:
            ImportError: If faiss-cpu is not installed.
        """
        try:
            import faiss  # type: ignore[import-not-found]

            return faiss
        except ImportError:
            raise ImportError(
                "faiss-cpu is required for vector search. "
                "Install with: pip install paper-index-tool[vector] "
                "or: uv sync --extra vector"
            )

    def _get_numpy(self) -> Any:
        """Import and return numpy module.

        Returns:
            The numpy module.

        Raises:
            ImportError: If numpy is not installed.
        """
        try:
            import numpy as np

            return np
        except ImportError:
            raise ImportError(
                "numpy is required for vector search. "
                "Install with: pip install paper-index-tool[vector] "
                "or: uv sync --extra vector"
            )

    def rebuild_index(self) -> dict[str, int | float]:
        """Rebuild the vector index from all entries.

        Chunks all papers, books, and media, generates embeddings
        via Bedrock, and builds a FAISS index for similarity search.

        For named indices, updates the index metadata with statistics.

        Returns:
            Dictionary with counts and cost:
            {"papers": N, "books": M, "media": P, "chunks": C, "tokens": T, "cost": $}.

        Example:
            >>> counts = searcher.rebuild_index()
            >>> print(f"Indexed {counts['chunks']} chunks, cost: ${counts['cost']:.6f}")
        """
        faiss = self._get_faiss()
        index_desc = f"'{self.index_name}'" if self.index_name else "(legacy)"
        logger.info("Rebuilding vector index %s", index_desc)

        # Collect all chunks
        all_chunks: list[Chunk] = []
        counts: dict[str, int | float] = {"papers": 0, "books": 0, "media": 0, "chunks": 0}

        # Chunk papers
        for paper in self.paper_registry.list_entries():
            text = paper.get_searchable_text()
            chunks = self.chunker.chunk_text(text, paper.id, "paper")
            all_chunks.extend(chunks)
            counts["papers"] += 1

        # Chunk books
        for book in self.book_registry.list_entries():
            text = book.get_searchable_text()
            chunks = self.chunker.chunk_text(text, book.id, "book")
            all_chunks.extend(chunks)
            counts["books"] += 1

        # Chunk media
        for media in self.media_registry.list_entries():
            text = media.get_searchable_text()
            chunks = self.chunker.chunk_text(text, media.id, "media")
            all_chunks.extend(chunks)
            counts["media"] += 1

        if not all_chunks:
            logger.warning("No content to index")
            counts["tokens"] = 0
            counts["cost"] = 0.0
            return counts

        # Apply character limit chunker to enforce model limits
        char_limit_chunker = self._get_char_limit_chunker()
        all_chunks = char_limit_chunker.process_chunks(all_chunks)

        counts["chunks"] = len(all_chunks)
        logger.info("Generating embeddings for %d chunks", len(all_chunks))

        # Generate embeddings
        texts = [chunk.text for chunk in all_chunks]
        embeddings_list, stats = self.embeddings.embed_texts(texts)

        # Store token/cost stats
        counts["tokens"] = stats.total_tokens
        counts["cost"] = stats.total_cost

        # Convert to numpy array
        np = self._get_numpy()
        embeddings_array = np.array(embeddings_list, dtype=np.float32)

        # Build FAISS index (Inner Product for cosine similarity with normalized vectors)
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatIP(dimension)

        # Normalize vectors for cosine similarity
        faiss.normalize_L2(embeddings_array)
        index.add(embeddings_array)

        # Save index to appropriate location
        if self.index_name:
            # Named index - use registry
            from paper_index_tool.vector.registry import VectorIndexRegistry

            registry = VectorIndexRegistry()
            registry.save_index_data(self.index_name, index, all_chunks)
            registry.update_index_stats(
                self.index_name,
                chunk_count=len(all_chunks),
                total_tokens=int(stats.total_tokens),
                estimated_cost_usd=stats.total_cost,
            )
        else:
            # Legacy single index
            index_dir = get_vector_index_dir()
            index_dir.mkdir(parents=True, exist_ok=True)

            faiss.write_index(index, str(get_faiss_index_path()))

            # Save chunk metadata
            chunks_data = [chunk.to_dict() for chunk in all_chunks]
            with open(get_chunks_path(), "w") as f:
                json.dump(chunks_data, f, indent=2)

        logger.info(
            "Vector index %s built: %d papers, %d books, %d media, %d chunks, %d tokens, $%.6f",
            index_desc,
            counts["papers"],
            counts["books"],
            counts["media"],
            counts["chunks"],
            counts["tokens"],
            counts["cost"],
        )

        # Clear cache
        self._index = None
        self._chunks = []

        return counts

    def _load_index(self) -> tuple[Any, list[Chunk]]:
        """Load FAISS index and chunk metadata.

        Returns:
            Tuple of (FAISS index, list of Chunks).

        Raises:
            IndexNotFoundError: If index doesn't exist.
            NamedIndexNotFoundError: If named index doesn't exist.
        """
        if self._index is not None and self._chunks:
            return self._index, self._chunks

        faiss = self._get_faiss()

        if self.index_name:
            # Named index - use registry
            from paper_index_tool.vector.registry import VectorIndexRegistry

            registry = VectorIndexRegistry()
            self._index, self._chunks = registry.load_index_data(self.index_name)
            logger.debug(
                "Loaded named index '%s' with %d chunks", self.index_name, len(self._chunks)
            )
            return self._index, self._chunks

        # Legacy single index
        index_path = get_faiss_index_path()
        chunks_path = get_chunks_path()

        if not index_path.exists() or not chunks_path.exists():
            raise IndexNotFoundError()

        try:
            self._index = faiss.read_index(str(index_path))

            with open(chunks_path) as f:
                chunks_data = json.load(f)
            self._chunks = [Chunk.from_dict(d) for d in chunks_data]

            logger.debug("Loaded vector index with %d chunks", len(self._chunks))
            return self._index, self._chunks
        except Exception as e:
            raise IndexNotFoundError() from e

    def search(
        self,
        query: str,
        entry_id: str | None = None,
        top_k: int = 10,
        extract_fragments_flag: bool = False,
        context_lines: int = 3,
        entry_types: list[EntryType] | None = None,
    ) -> list[SearchResult]:
        """Search using semantic similarity.

        Embeds the query and finds the most similar chunks using
        cosine similarity. Results are aggregated by entry and
        returned as SearchResult objects.

        Args:
            query: Natural language query (can be a full sentence/question).
            entry_id: If provided, filter results to this entry only.
            top_k: Number of results to return.
            extract_fragments_flag: If True, extract matching text fragments.
            context_lines: Context lines around matches in fragments.
            entry_types: Optional list of entry types to search.

        Returns:
            List of SearchResult objects sorted by similarity score.

        Example:
            >>> results = searcher.search(
            ...     "How do individuals develop as leaders?",
            ...     top_k=5
            ... )
        """
        logger.info("Semantic search for: %s", query[:100])

        faiss = self._get_faiss()
        np = self._get_numpy()
        index, chunks = self._load_index()

        # Embed query (uses TEXT_RETRIEVAL purpose for Nova model)
        query_embedding = self.embeddings.embed_query(query)
        query_array = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_array)

        # Search index
        # Get more results than needed since we'll aggregate by entry
        search_k = min(top_k * 10, len(chunks))
        distances, indices = index.search(query_array, search_k)

        # Aggregate results by entry
        entry_scores: dict[str, tuple[float, Chunk]] = {}

        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(chunks):
                continue

            chunk = chunks[idx]
            score = float(distances[0][i])

            # Filter by entry_id if specified
            if entry_id and chunk.entry_id != entry_id:
                continue

            # Filter by entry_type if specified
            if entry_types:
                chunk_type = EntryType(chunk.entry_type)
                if chunk_type not in entry_types:
                    continue

            # Keep best score per entry
            if chunk.entry_id not in entry_scores or score > entry_scores[chunk.entry_id][0]:
                entry_scores[chunk.entry_id] = (score, chunk)

        # Build results
        results: list[SearchResult] = []
        query_terms = query.split()  # For fragment extraction

        for entry_id_key, (score, chunk) in sorted(
            entry_scores.items(), key=lambda x: x[1][0], reverse=True
        )[:top_k]:
            # Get full entry
            entry: Paper | Book | Media | None = None
            entry_type = EntryType(chunk.entry_type)

            if entry_type == EntryType.PAPER:
                entry = self.paper_registry.get_paper(entry_id_key)
            elif entry_type == EntryType.BOOK:
                entry = self.book_registry.get_book(entry_id_key)
            elif entry_type == EntryType.MEDIA:
                entry = self.media_registry.get_media(entry_id_key)

            # Get full content for fragments
            content = entry.get_searchable_text() if entry else chunk.text

            # Extract fragments if requested
            fragments: list[dict[str, Any]] = []
            if extract_fragments_flag:
                fragments = extract_fragments(content, query_terms, context_lines, max_fragments=3)

            # Create result
            result = SearchResult(
                entry_id=entry_id_key,
                score=score,
                content=content,
                entry_type=entry_type,
                paper=entry if isinstance(entry, Paper) else None,
                book=entry if isinstance(entry, Book) else None,
                media=entry if isinstance(entry, Media) else None,
                fragments=fragments,
            )
            results.append(result)

        logger.info("Found %d semantic results", len(results))
        return results

    def index_exists(self) -> bool:
        """Check if vector index exists.

        Returns:
            True if index exists, False otherwise.
        """
        if self.index_name:
            # Named index - check via registry
            faiss_path = get_named_index_faiss_path(self.index_name)
            chunks_path = get_named_index_chunks_path(self.index_name)
            return faiss_path.exists() and chunks_path.exists()

        # Legacy single index
        return get_faiss_index_path().exists() and get_chunks_path().exists()
