"""BM25 search functionality for paper-index-tool.

This module provides BM25 full-text search capabilities for academic papers
and books. It supports searching within individual entries, across all entries
of a type, or across the entire corpus (papers and books combined).

Classes:
    SearchResult: Container for search results with score and fragments.
    PaperSearcher: BM25 search across papers (stores index at bm25s/papers).
    BookSearcher: BM25 search across books (stores index at bm25s/books).
    CombinedSearcher: BM25 search across both papers and books.

Functions:
    extract_fragments: Extract text fragments containing query terms.
    ensure_index_current: Ensure the paper BM25 index is up to date.
    ensure_all_indices_current: Ensure both paper and book indices are up to date.

Entry Types:
    - "paper": Academic peer-reviewed paper.
    - "book": Book or book chapter.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

import bm25s  # type: ignore[import-untyped]
import Stemmer  # type: ignore[import-not-found]

from paper_index_tool.logging_config import get_logger
from paper_index_tool.models import Book, Media, Paper
from paper_index_tool.storage import BookRegistry, MediaRegistry, PaperRegistry, get_bm25_index_dir

logger = get_logger(__name__)


# =============================================================================
# Entry Type Enum
# =============================================================================


class EntryType(str, Enum):
    """Entry type enumeration for search results.

    Distinguishes between papers, books, and media in search results,
    enabling type-specific processing and display.

    Values:
        PAPER: Academic peer-reviewed paper.
        BOOK: Book or book chapter.
        MEDIA: Video, podcast, or blog content.
    """

    PAPER = "paper"
    BOOK = "book"
    MEDIA = "media"


# =============================================================================
# Search Result
# =============================================================================


class SearchResult:
    """Container for a search result with score and fragments.

    Holds the result of a BM25 search including the entry ID, relevance score,
    matched content, optional full entry object, and extracted text fragments.

    Attributes:
        entry_id: Unique identifier for the entry (paper, book, or media).
        score: BM25 relevance score (higher is more relevant).
        content: Full searchable content that was matched.
        entry_type: Type of entry (paper, book, or media).
        paper: Paper object if entry_type is PAPER (for backward compatibility).
        book: Book object if entry_type is BOOK.
        media: Media object if entry_type is MEDIA.
        fragments: List of text fragments containing matches.

    Backward Compatibility:
        The paper_id property is provided for backward compatibility with
        code that expects paper-only search results.

    Example:
        >>> result = SearchResult(
        ...     entry_id="ashford2012",
        ...     score=5.67,
        ...     content="Leadership development...",
        ...     entry_type=EntryType.PAPER,
        ...     paper=paper_obj
        ... )
        >>> result.paper_id  # backward compatible
        'ashford2012'
    """

    def __init__(
        self,
        entry_id: str,
        score: float,
        content: str,
        entry_type: EntryType = EntryType.PAPER,
        paper: Paper | None = None,
        book: Book | None = None,
        media: Media | None = None,
        fragments: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize a search result.

        Args:
            entry_id: Unique identifier for the entry.
            score: BM25 relevance score.
            content: Full searchable content that was matched.
            entry_type: Type of entry (paper, book, or media).
            paper: Paper object if entry_type is PAPER.
            book: Book object if entry_type is BOOK.
            media: Media object if entry_type is MEDIA.
            fragments: List of extracted text fragments.
        """
        self.entry_id = entry_id
        self.score = score
        self.content = content
        self.entry_type = entry_type
        self.paper = paper
        self.book = book
        self.media = media
        self.fragments = fragments or []

    @property
    def paper_id(self) -> str:
        """Get entry ID (backward compatibility alias).

        Returns:
            The entry_id value.

        Note:
            This property is provided for backward compatibility with
            code that expects paper-only search results.
        """
        return self.entry_id

    @property
    def entry(self) -> Paper | Book | Media | None:
        """Get the entry object (Paper, Book, or Media).

        Returns:
            The Paper, Book, or Media object, or None if not loaded.
        """
        if self.entry_type == EntryType.PAPER:
            return self.paper
        if self.entry_type == EntryType.BOOK:
            return self.book
        return self.media


# =============================================================================
# Fragment Extraction
# =============================================================================


def extract_fragments(
    content: str,
    query_terms: list[str],
    context_lines: int = 3,
    max_fragments: int = 3,
) -> list[dict[str, Any]]:
    """Extract text fragments containing query terms with context.

    Searches through content line by line to find matches for query terms,
    then extracts those lines with surrounding context. Adjacent or
    overlapping fragments are merged to avoid duplication.

    Args:
        content: Full document content to search.
        query_terms: List of query terms to find (case-insensitive).
        context_lines: Number of context lines before/after match.
        max_fragments: Maximum number of fragments to extract.

    Returns:
        List of fragment dictionaries with keys:
            - line_start: Starting line number (1-based).
            - line_end: Ending line number (1-based).
            - lines: List of text lines in the fragment.
            - matched_line_numbers: List of line numbers containing matches.

    Example:
        >>> content = "Line 1\\nLeadership development\\nLine 3"
        >>> fragments = extract_fragments(content, ["leadership"], context_lines=1)
        >>> fragments[0]["matched_line_numbers"]
        [2]
    """
    if not content or not query_terms:
        return []

    lines = content.splitlines()
    if not lines:
        return []

    # Find all lines containing any query term
    matched_lines = set()
    query_terms_lower = [term.lower() for term in query_terms]

    for line_idx, line in enumerate(lines):
        line_lower = line.lower()
        for term in query_terms_lower:
            if term in line_lower:
                matched_lines.add(line_idx)
                break

    if not matched_lines:
        return []

    # Sort matched lines
    sorted_matches = sorted(matched_lines)

    # Build fragments with context, merging overlapping ranges
    fragments: list[dict[str, Any]] = []
    current_fragment: dict[str, Any] | None = None

    for match_idx in sorted_matches:
        start = max(0, match_idx - context_lines)
        end = min(len(lines) - 1, match_idx + context_lines)

        if current_fragment is None:
            current_fragment = {
                "line_start": start + 1,
                "line_end": end + 1,
                "lines": lines[start : end + 1],
                "matched_line_numbers": [match_idx + 1],
            }
        else:
            current_end = current_fragment["line_end"] - 1

            if start <= current_end + 1:
                # Overlapping - extend
                new_end = max(current_end, end)
                current_fragment["line_end"] = new_end + 1
                current_fragment["lines"] = lines[current_fragment["line_start"] - 1 : new_end + 1]
                current_fragment["matched_line_numbers"].append(match_idx + 1)
            else:
                fragments.append(current_fragment)
                if len(fragments) >= max_fragments:
                    break
                current_fragment = {
                    "line_start": start + 1,
                    "line_end": end + 1,
                    "lines": lines[start : end + 1],
                    "matched_line_numbers": [match_idx + 1],
                }

    if current_fragment and len(fragments) < max_fragments:
        fragments.append(current_fragment)

    return fragments


# =============================================================================
# Base Searcher (Abstract)
# =============================================================================


class BaseSearcher(ABC):
    """Abstract base class for BM25 searchers.

    Provides common BM25 search functionality that can be specialized
    for different entry types (papers, books). Subclasses must implement
    the abstract properties and methods to define their specific behavior.

    This class follows SOLID principles:
        - SRP: Only handles BM25 search logic.
        - OCP: Extensible via subclassing without modification.
        - LSP: Subclasses are interchangeable for search operations.
        - ISP: Small, focused interface for search operations.
        - DIP: Depends on abstractions (registry interface).

    Abstract Properties:
        entry_type: The type of entries this searcher handles.
        index_subdir: Subdirectory name for the BM25 index.

    Abstract Methods:
        _get_registry: Get the registry instance for this entry type.
        _get_entry: Get a single entry by ID from the registry.
        _create_result: Create a SearchResult for an entry.

    Methods:
        rebuild_index: Rebuild the BM25 index from all entries.
        search: Search entries using BM25.
    """

    def __init__(self) -> None:
        """Initialize the base searcher.

        Sets up the BM25 stemmer and initializes cache variables.
        The index path is derived from the index_subdir property.
        """
        self.stemmer = Stemmer.Stemmer("english")
        self._retriever: bm25s.BM25 | None = None
        self._corpus: list[dict[str, str]] | None = None

    @property
    @abstractmethod
    def entry_type(self) -> EntryType:
        """Get the entry type for this searcher.

        Returns:
            EntryType.PAPER or EntryType.BOOK.
        """
        ...

    @property
    @abstractmethod
    def index_subdir(self) -> str:
        """Get the subdirectory name for the BM25 index.

        Returns:
            Subdirectory name (e.g., "papers" or "books").
        """
        ...

    @abstractmethod
    def _get_registry(self) -> PaperRegistry | BookRegistry | MediaRegistry:
        """Get the registry instance for this entry type.

        Returns:
            PaperRegistry, BookRegistry, or MediaRegistry instance.
        """
        ...

    @abstractmethod
    def _get_entry(self, entry_id: str) -> Paper | Book | Media | None:
        """Get an entry by ID from the registry.

        Args:
            entry_id: The entry ID to look up.

        Returns:
            Paper, Book, or Media object, or None if not found.
        """
        ...

    @abstractmethod
    def _create_result(
        self,
        entry_id: str,
        score: float,
        content: str,
        entry: Paper | Book | Media | None,
        fragments: list[dict[str, Any]],
    ) -> SearchResult:
        """Create a SearchResult for an entry.

        Args:
            entry_id: The entry ID.
            score: BM25 relevance score.
            content: Matched content.
            entry: Paper, Book, or Media object.
            fragments: Extracted text fragments.

        Returns:
            SearchResult with appropriate entry_type and entry object.
        """
        ...

    @property
    def index_path(self) -> Path:
        """Get path to BM25 index directory.

        Returns:
            Path to the index directory (e.g., bm25s/papers).
        """
        return get_bm25_index_dir() / self.index_subdir

    def _needs_rebuild(self) -> bool:
        """Check if index needs to be rebuilt.

        Returns:
            True if index doesn't exist, False otherwise.
        """
        if not self.index_path.exists():
            return True
        # Could add timestamp checking here for cache invalidation
        return False

    def rebuild_index(self) -> int:
        """Rebuild the BM25 index from all entries.

        Retrieves all entries from the registry, extracts their searchable
        text, tokenizes with stemming, and builds a new BM25 index.
        The index is saved to disk for later retrieval.

        Returns:
            Number of entries indexed.

        Example:
            >>> searcher = PaperSearcher()
            >>> count = searcher.rebuild_index()
            >>> print(f"Indexed {count} papers")
        """
        logger.info("Rebuilding BM25 index for %ss", self.entry_type.value)

        registry = self._get_registry()
        entries = registry.list_entries()
        if not entries:
            logger.warning("No %ss to index", self.entry_type.value)
            return 0

        # Build corpus
        corpus = []
        for entry in entries:
            text = entry.get_searchable_text()
            if text:
                corpus.append(
                    {
                        "id": entry.id,
                        "content": text,
                    }
                )

        if not corpus:
            logger.warning("No searchable content found")
            return 0

        # Tokenize
        texts = [doc["content"] for doc in corpus]
        corpus_tokens = bm25s.tokenize(texts, stopwords="en", stemmer=self.stemmer)

        # Create index
        retriever = bm25s.BM25()
        retriever.index(corpus_tokens)

        # Save
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        retriever.save(str(self.index_path), corpus=corpus)

        logger.info("Indexed %d %ss", len(corpus), self.entry_type.value)
        self._retriever = None  # Clear cache
        self._corpus = None
        return len(corpus)

    def _load_index(self) -> tuple[bm25s.BM25, list[dict[str, str]]]:
        """Load the BM25 index from disk.

        Loads the saved BM25 index and corpus from disk. Uses memory
        mapping for efficient access to large indices.

        Returns:
            Tuple of (retriever, corpus).

        Raises:
            ValueError: If index not found or failed to load.
        """
        if self._retriever is not None and self._corpus is not None:
            return self._retriever, self._corpus

        if not self.index_path.exists():
            raise ValueError(
                f"Index not found for {self.entry_type.value}s. Run rebuild_index() first."
            )

        try:
            self._retriever = bm25s.BM25.load(str(self.index_path), load_corpus=True, mmap=True)
            corpus_data = self._retriever.corpus
            self._corpus = list(corpus_data) if corpus_data is not None else []
            return self._retriever, self._corpus
        except Exception as e:
            raise ValueError(f"Failed to load index: {e}")

    def search(
        self,
        query: str,
        entry_id: str | None = None,
        top_k: int = 10,
        extract_fragments_flag: bool = False,
        context_lines: int = 3,
    ) -> list[SearchResult]:
        """Search entries using BM25.

        Performs BM25 full-text search across all entries or within a
        single entry. Optionally extracts matching text fragments with
        surrounding context.

        Args:
            query: Search query string.
            entry_id: If provided, search only this entry. If None, search all.
            top_k: Number of results to return.
            extract_fragments_flag: If True, extract matching text fragments.
            context_lines: Context lines around matches in fragments.

        Returns:
            List of SearchResult objects sorted by relevance score.

        Example:
            >>> searcher = PaperSearcher()
            >>> results = searcher.search("leadership development", top_k=5)
            >>> for r in results:
            ...     print(f"{r.entry_id}: {r.score:.2f}")
        """
        logger.info("Searching %ss for: %s", self.entry_type.value, query)

        # For single entry search, we can do it directly without the full index
        if entry_id:
            return self._search_single_entry(query, entry_id, extract_fragments_flag, context_lines)

        # Search all entries via index
        try:
            retriever, corpus = self._load_index()
        except ValueError:
            # Try to rebuild index
            count = self.rebuild_index()
            if count == 0:
                return []
            retriever, corpus = self._load_index()

        # Tokenize query
        query_tokens = bm25s.tokenize([query], stopwords="en", stemmer=self.stemmer)

        # Search
        actual_k = min(top_k, len(corpus))
        if actual_k == 0:
            return []

        results_array, scores_array = retriever.retrieve(query_tokens, k=actual_k)

        # Build results
        results: list[SearchResult] = []
        query_terms = query.split()

        for i in range(results_array.shape[1]):
            doc = results_array[0, i]
            score = float(scores_array[0, i])

            if score <= 0:
                continue

            doc_id = doc["id"]
            content = doc["content"]

            # Get full entry
            entry = self._get_entry(doc_id)

            # Extract fragments if requested
            fragments: list[dict[str, Any]] = []
            if extract_fragments_flag:
                fragments = extract_fragments(content, query_terms, context_lines, max_fragments=3)

            results.append(
                self._create_result(
                    entry_id=doc_id,
                    score=score,
                    content=content,
                    entry=entry,
                    fragments=fragments,
                )
            )

        logger.info("Found %d results", len(results))
        return results

    def _search_single_entry(
        self,
        query: str,
        entry_id: str,
        extract_fragments_flag: bool,
        context_lines: int,
    ) -> list[SearchResult]:
        """Search within a single entry's content.

        Uses simple BM25 scoring on just this entry's content without
        requiring the full index.

        Args:
            query: Search query string.
            entry_id: Entry ID to search within.
            extract_fragments_flag: If True, extract matching text fragments.
            context_lines: Context lines around matches.

        Returns:
            List with single SearchResult or empty list if no match.

        Raises:
            ValueError: If entry not found.
        """
        entry = self._get_entry(entry_id)
        if not entry:
            raise ValueError(f"{self.entry_type.value.capitalize()} '{entry_id}' not found")

        content = entry.get_searchable_text()
        if not content:
            return []

        # Simple BM25 on single document
        corpus_tokens = bm25s.tokenize([content], stopwords="en", stemmer=self.stemmer)
        query_tokens = bm25s.tokenize([query], stopwords="en", stemmer=self.stemmer)

        retriever = bm25s.BM25()
        retriever.index(corpus_tokens)
        _results_array, scores_array = retriever.retrieve(query_tokens, k=1)

        score = float(scores_array[0, 0])
        if score <= 0:
            return []

        # Extract fragments
        query_terms = query.split()
        fragments: list[dict[str, Any]] = []
        if extract_fragments_flag:
            fragments = extract_fragments(content, query_terms, context_lines, max_fragments=3)

        return [
            self._create_result(
                entry_id=entry_id,
                score=score,
                content=content,
                entry=entry,
                fragments=fragments,
            )
        ]


# =============================================================================
# Paper Searcher
# =============================================================================


class PaperSearcher(BaseSearcher):
    """BM25 search across papers.

    Provides full-text search capabilities for academic papers stored in
    the paper registry. The search index is stored at bm25s/papers.

    Inherits from BaseSearcher and provides paper-specific implementations
    for registry access and result creation.

    Attributes:
        registry: PaperRegistry instance for accessing papers.

    Example:
        >>> searcher = PaperSearcher()
        >>> searcher.rebuild_index()
        15
        >>> results = searcher.search("leadership development")
        >>> for r in results:
        ...     print(f"{r.paper_id}: {r.score:.2f}")
    """

    def __init__(self) -> None:
        """Initialize the paper searcher.

        Creates a PaperRegistry instance and initializes the base searcher.
        """
        super().__init__()
        self.registry = PaperRegistry()

    @property
    def entry_type(self) -> EntryType:
        """Get the entry type for papers.

        Returns:
            EntryType.PAPER.
        """
        return EntryType.PAPER

    @property
    def index_subdir(self) -> str:
        """Get the index subdirectory for papers.

        Returns:
            "papers".
        """
        return "papers"

    def _get_registry(self) -> PaperRegistry:
        """Get the paper registry.

        Returns:
            PaperRegistry instance.
        """
        return self.registry

    def _get_entry(self, entry_id: str) -> Paper | None:
        """Get a paper by ID.

        Args:
            entry_id: Paper ID to look up.

        Returns:
            Paper object or None if not found.
        """
        return self.registry.get_paper(entry_id)

    def _create_result(
        self,
        entry_id: str,
        score: float,
        content: str,
        entry: Paper | Book | Media | None,
        fragments: list[dict[str, Any]],
    ) -> SearchResult:
        """Create a SearchResult for a paper.

        Args:
            entry_id: Paper ID.
            score: BM25 relevance score.
            content: Matched content.
            entry: Paper object.
            fragments: Extracted text fragments.

        Returns:
            SearchResult with entry_type=PAPER and paper set.
        """
        paper = entry if isinstance(entry, Paper) else None
        return SearchResult(
            entry_id=entry_id,
            score=score,
            content=content,
            entry_type=EntryType.PAPER,
            paper=paper,
            fragments=fragments,
        )

    def _get_index_path(self) -> Path:
        """Get path to BM25 index directory.

        Returns:
            Path to the index directory.

        Note:
            This method is provided for backward compatibility.
            New code should use the index_path property instead.
        """
        return self.index_path

    def search_paper(
        self,
        query: str,
        paper_id: str | None = None,
        top_k: int = 10,
        extract_fragments_flag: bool = False,
        context_lines: int = 3,
    ) -> list[SearchResult]:
        """Search papers using BM25 (backward compatibility method).

        This method provides backward compatibility for code that uses
        paper_id parameter. New code should use search() with entry_id.

        Args:
            query: Search query string.
            paper_id: If provided, search only this paper. If None, search all.
            top_k: Number of results to return.
            extract_fragments_flag: If True, extract matching text fragments.
            context_lines: Context lines around matches in fragments.

        Returns:
            List of SearchResult objects sorted by relevance score.

        Example:
            >>> searcher = PaperSearcher()
            >>> results = searcher.search_paper("leadership", paper_id="ashford2012")
        """
        return self.search(
            query=query,
            entry_id=paper_id,
            top_k=top_k,
            extract_fragments_flag=extract_fragments_flag,
            context_lines=context_lines,
        )


# =============================================================================
# Book Searcher
# =============================================================================


class BookSearcher(BaseSearcher):
    """BM25 search across books.

    Provides full-text search capabilities for books and book chapters
    stored in the book registry. The search index is stored at bm25s/books.

    Inherits from BaseSearcher and provides book-specific implementations
    for registry access and result creation.

    Attributes:
        registry: BookRegistry instance for accessing books.

    Example:
        >>> searcher = BookSearcher()
        >>> searcher.rebuild_index()
        10
        >>> results = searcher.search("organizational behavior")
        >>> for r in results:
        ...     print(f"{r.entry_id}: {r.score:.2f}")
    """

    def __init__(self) -> None:
        """Initialize the book searcher.

        Creates a BookRegistry instance and initializes the base searcher.
        """
        super().__init__()
        self.registry = BookRegistry()

    @property
    def entry_type(self) -> EntryType:
        """Get the entry type for books.

        Returns:
            EntryType.BOOK.
        """
        return EntryType.BOOK

    @property
    def index_subdir(self) -> str:
        """Get the index subdirectory for books.

        Returns:
            "books".
        """
        return "books"

    def _get_registry(self) -> BookRegistry:
        """Get the book registry.

        Returns:
            BookRegistry instance.
        """
        return self.registry

    def _get_entry(self, entry_id: str) -> Book | None:
        """Get a book by ID.

        Args:
            entry_id: Book ID to look up.

        Returns:
            Book object or None if not found.
        """
        return self.registry.get_book(entry_id)

    def _create_result(
        self,
        entry_id: str,
        score: float,
        content: str,
        entry: Paper | Book | Media | None,
        fragments: list[dict[str, Any]],
    ) -> SearchResult:
        """Create a SearchResult for a book.

        Args:
            entry_id: Book ID.
            score: BM25 relevance score.
            content: Matched content.
            entry: Book object.
            fragments: Extracted text fragments.

        Returns:
            SearchResult with entry_type=BOOK and book set.
        """
        book = entry if isinstance(entry, Book) else None
        return SearchResult(
            entry_id=entry_id,
            score=score,
            content=content,
            entry_type=EntryType.BOOK,
            book=book,
            fragments=fragments,
        )


# =============================================================================
# Media Searcher
# =============================================================================


class MediaSearcher(BaseSearcher):
    """BM25 search across media (video, podcast, blog).

    Provides full-text search capabilities for media content stored in
    the media registry. The search index is stored at bm25s/media.

    Inherits from BaseSearcher and provides media-specific implementations
    for registry access and result creation.

    Attributes:
        registry: MediaRegistry instance for accessing media.

    Example:
        >>> searcher = MediaSearcher()
        >>> searcher.rebuild_index()
        8
        >>> results = searcher.search("leadership podcast")
        >>> for r in results:
        ...     print(f"{r.entry_id}: {r.score:.2f}")
    """

    def __init__(self) -> None:
        """Initialize the media searcher.

        Creates a MediaRegistry instance and initializes the base searcher.
        """
        super().__init__()
        self.registry = MediaRegistry()

    @property
    def entry_type(self) -> EntryType:
        """Get the entry type for media.

        Returns:
            EntryType.MEDIA.
        """
        return EntryType.MEDIA

    @property
    def index_subdir(self) -> str:
        """Get the index subdirectory for media.

        Returns:
            "media".
        """
        return "media"

    def _get_registry(self) -> MediaRegistry:
        """Get the media registry.

        Returns:
            MediaRegistry instance.
        """
        return self.registry

    def _get_entry(self, entry_id: str) -> Media | None:
        """Get a media entry by ID.

        Args:
            entry_id: Media ID to look up.

        Returns:
            Media object or None if not found.
        """
        return self.registry.get_media(entry_id)

    def _create_result(
        self,
        entry_id: str,
        score: float,
        content: str,
        entry: Paper | Book | Media | None,
        fragments: list[dict[str, Any]],
    ) -> SearchResult:
        """Create a SearchResult for a media entry.

        Args:
            entry_id: Media ID.
            score: BM25 relevance score.
            content: Matched content.
            entry: Media object.
            fragments: Extracted text fragments.

        Returns:
            SearchResult with entry_type=MEDIA and media set.
        """
        media = entry if isinstance(entry, Media) else None
        return SearchResult(
            entry_id=entry_id,
            score=score,
            content=content,
            entry_type=EntryType.MEDIA,
            media=media,
            fragments=fragments,
        )


# =============================================================================
# Combined Searcher
# =============================================================================


class CombinedSearcher:
    """BM25 search across papers, books, and media.

    Provides unified full-text search capabilities across the entire
    corpus of papers, books, and media. Results are merged and sorted by
    relevance score.

    This class combines results from PaperSearcher, BookSearcher, and
    MediaSearcher, providing a single interface for searching all academic content.

    Attributes:
        paper_searcher: PaperSearcher instance.
        book_searcher: BookSearcher instance.
        media_searcher: MediaSearcher instance.

    Example:
        >>> searcher = CombinedSearcher()
        >>> searcher.rebuild_all_indices()
        {'papers': 15, 'books': 10, 'media': 8}
        >>> results = searcher.search("leadership", top_k=10)
        >>> for r in results:
        ...     print(f"[{r.entry_type.value}] {r.entry_id}: {r.score:.2f}")
    """

    def __init__(self) -> None:
        """Initialize the combined searcher.

        Creates PaperSearcher, BookSearcher, and MediaSearcher instances.
        """
        self.paper_searcher = PaperSearcher()
        self.book_searcher = BookSearcher()
        self.media_searcher = MediaSearcher()

    def rebuild_all_indices(self) -> dict[str, int]:
        """Rebuild paper, book, and media BM25 indices.

        Rebuilds the search indices for papers, books, and media.

        Returns:
            Dictionary with counts: {"papers": N, "books": M, "media": P}.

        Example:
            >>> searcher = CombinedSearcher()
            >>> counts = searcher.rebuild_all_indices()
            >>> print(f"Indexed {counts['papers']} papers, {counts['books']} books")
        """
        logger.info("Rebuilding all BM25 indices")
        paper_count = self.paper_searcher.rebuild_index()
        book_count = self.book_searcher.rebuild_index()
        media_count = self.media_searcher.rebuild_index()
        return {"papers": paper_count, "books": book_count, "media": media_count}

    def search(
        self,
        query: str,
        top_k: int = 10,
        extract_fragments_flag: bool = False,
        context_lines: int = 3,
        entry_types: list[EntryType] | None = None,
    ) -> list[SearchResult]:
        """Search across papers, books, and media using BM25.

        Performs BM25 full-text search across the combined corpus of
        papers, books, and media. Results are merged and sorted by relevance score.

        Args:
            query: Search query string.
            top_k: Total number of results to return (from combined corpus).
            extract_fragments_flag: If True, extract matching text fragments.
            context_lines: Context lines around matches in fragments.
            entry_types: Optional list of entry types to search. If None,
                        searches papers, books, and media.

        Returns:
            List of SearchResult objects sorted by relevance score.

        Example:
            >>> searcher = CombinedSearcher()
            >>> results = searcher.search("leadership", top_k=10)
            >>> papers = [r for r in results if r.entry_type == EntryType.PAPER]
            >>> books = [r for r in results if r.entry_type == EntryType.BOOK]
            >>> media = [r for r in results if r.entry_type == EntryType.MEDIA]
        """
        logger.info("Combined search for: %s", query)

        # Determine which types to search
        if entry_types is None:
            entry_types = [EntryType.PAPER, EntryType.BOOK, EntryType.MEDIA]

        all_results: list[SearchResult] = []

        # Search papers
        if EntryType.PAPER in entry_types:
            try:
                paper_results = self.paper_searcher.search(
                    query=query,
                    top_k=top_k,  # Get more results, we'll trim later
                    extract_fragments_flag=extract_fragments_flag,
                    context_lines=context_lines,
                )
                all_results.extend(paper_results)
            except ValueError as e:
                logger.warning("Paper search failed: %s", e)

        # Search books
        if EntryType.BOOK in entry_types:
            try:
                book_results = self.book_searcher.search(
                    query=query,
                    top_k=top_k,  # Get more results, we'll trim later
                    extract_fragments_flag=extract_fragments_flag,
                    context_lines=context_lines,
                )
                all_results.extend(book_results)
            except ValueError as e:
                logger.warning("Book search failed: %s", e)

        # Search media
        if EntryType.MEDIA in entry_types:
            try:
                media_results = self.media_searcher.search(
                    query=query,
                    top_k=top_k,  # Get more results, we'll trim later
                    extract_fragments_flag=extract_fragments_flag,
                    context_lines=context_lines,
                )
                all_results.extend(media_results)
            except ValueError as e:
                logger.warning("Media search failed: %s", e)

        # Sort by score and limit to top_k
        all_results.sort(key=lambda r: r.score, reverse=True)
        results = all_results[:top_k]

        logger.info("Found %d combined results", len(results))
        return results

    def search_papers_only(
        self,
        query: str,
        paper_id: str | None = None,
        top_k: int = 10,
        extract_fragments_flag: bool = False,
        context_lines: int = 3,
    ) -> list[SearchResult]:
        """Search only papers using BM25.

        Convenience method that delegates to PaperSearcher.

        Args:
            query: Search query string.
            paper_id: If provided, search only this paper.
            top_k: Number of results to return.
            extract_fragments_flag: If True, extract matching text fragments.
            context_lines: Context lines around matches.

        Returns:
            List of SearchResult objects (all with entry_type=PAPER).
        """
        return self.paper_searcher.search(
            query=query,
            entry_id=paper_id,
            top_k=top_k,
            extract_fragments_flag=extract_fragments_flag,
            context_lines=context_lines,
        )

    def search_books_only(
        self,
        query: str,
        book_id: str | None = None,
        top_k: int = 10,
        extract_fragments_flag: bool = False,
        context_lines: int = 3,
    ) -> list[SearchResult]:
        """Search only books using BM25.

        Convenience method that delegates to BookSearcher.

        Args:
            query: Search query string.
            book_id: If provided, search only this book.
            top_k: Number of results to return.
            extract_fragments_flag: If True, extract matching text fragments.
            context_lines: Context lines around matches.

        Returns:
            List of SearchResult objects (all with entry_type=BOOK).
        """
        return self.book_searcher.search(
            query=query,
            entry_id=book_id,
            top_k=top_k,
            extract_fragments_flag=extract_fragments_flag,
            context_lines=context_lines,
        )

    def search_media_only(
        self,
        query: str,
        media_id: str | None = None,
        top_k: int = 10,
        extract_fragments_flag: bool = False,
        context_lines: int = 3,
    ) -> list[SearchResult]:
        """Search only media using BM25.

        Convenience method that delegates to MediaSearcher.

        Args:
            query: Search query string.
            media_id: If provided, search only this media entry.
            top_k: Number of results to return.
            extract_fragments_flag: If True, extract matching text fragments.
            context_lines: Context lines around matches.

        Returns:
            List of SearchResult objects (all with entry_type=MEDIA).
        """
        return self.media_searcher.search(
            query=query,
            entry_id=media_id,
            top_k=top_k,
            extract_fragments_flag=extract_fragments_flag,
            context_lines=context_lines,
        )


# =============================================================================
# Utility Functions
# =============================================================================


def ensure_index_current() -> None:
    """Ensure the paper BM25 index is up to date.

    Checks if the paper index needs to be rebuilt and rebuilds it
    if necessary. This function is provided for backward compatibility.

    Example:
        >>> ensure_index_current()  # Rebuilds if needed
    """
    searcher = PaperSearcher()
    if searcher._needs_rebuild():
        searcher.rebuild_index()


def ensure_all_indices_current() -> None:
    """Ensure paper, book, and media BM25 indices are up to date.

    Checks if any index needs to be rebuilt and rebuilds them
    if necessary.

    Example:
        >>> ensure_all_indices_current()  # Rebuilds if needed
    """
    paper_searcher = PaperSearcher()
    if paper_searcher._needs_rebuild():
        paper_searcher.rebuild_index()

    book_searcher = BookSearcher()
    if book_searcher._needs_rebuild():
        book_searcher.rebuild_index()

    media_searcher = MediaSearcher()
    if media_searcher._needs_rebuild():
        media_searcher.rebuild_index()
