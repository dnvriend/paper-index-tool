"""Vector index registry for managing named indices.

This module provides a registry for managing multiple named vector indices.
Each index has its own configuration (model, dimensions) and storage location.

Classes:
    VectorIndexRegistry: Registry for managing named vector indices.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from paper_index_tool.logging_config import get_logger
from paper_index_tool.models import VectorIndexMetadata
from paper_index_tool.storage.paths import (
    get_named_index_chunks_path,
    get_named_index_dir,
    get_named_index_faiss_path,
    get_named_index_metadata_path,
    get_vector_indices_path,
)
from paper_index_tool.vector.chunking import Chunk
from paper_index_tool.vector.embeddings import (
    get_model_config,
    validate_dimensions,
)
from paper_index_tool.vector.errors import NamedIndexNotFoundError

logger = get_logger(__name__)


class VectorIndexRegistry:
    """Registry for managing named vector indices.

    Provides CRUD operations for named vector indices, each with its own
    embedding model configuration and storage location.

    Example:
        >>> registry = VectorIndexRegistry()
        >>> registry.create_index("nova-1024", model_name="nova", dimensions=1024)
        >>> indices = registry.list_indices()
        >>> registry.delete_index("nova-1024")
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        self._indices: dict[str, VectorIndexMetadata] | None = None

    def _load_indices(self) -> dict[str, VectorIndexMetadata]:
        """Load indices registry from disk.

        Returns:
            Dictionary mapping index names to their metadata.
        """
        if self._indices is not None:
            return self._indices

        indices_path = get_vector_indices_path()
        if not indices_path.exists():
            self._indices = {}
            return self._indices

        try:
            with open(indices_path) as f:
                data = json.load(f)

            self._indices = {}
            for name, index_data in data.items():
                # Parse datetime strings
                if "created_at" in index_data and isinstance(index_data["created_at"], str):
                    index_data["created_at"] = datetime.fromisoformat(index_data["created_at"])
                if "updated_at" in index_data and isinstance(index_data["updated_at"], str):
                    index_data["updated_at"] = datetime.fromisoformat(index_data["updated_at"])

                self._indices[name] = VectorIndexMetadata(**index_data)

            return self._indices
        except Exception as e:
            logger.warning("Failed to load indices registry: %s", e)
            self._indices = {}
            return self._indices

    def _save_indices(self) -> None:
        """Save indices registry to disk."""
        indices_path = get_vector_indices_path()
        indices_path.parent.mkdir(parents=True, exist_ok=True)

        indices = self._load_indices()
        data: dict[str, Any] = {}

        for name, metadata in indices.items():
            index_data = metadata.model_dump()
            # Convert datetime to ISO format strings
            if isinstance(index_data.get("created_at"), datetime):
                index_data["created_at"] = index_data["created_at"].isoformat()
            if isinstance(index_data.get("updated_at"), datetime):
                index_data["updated_at"] = index_data["updated_at"].isoformat()
            data[name] = index_data

        with open(indices_path, "w") as f:
            json.dump(data, f, indent=2)

    def list_indices(self) -> list[VectorIndexMetadata]:
        """List all registered vector indices.

        Returns:
            List of VectorIndexMetadata objects.
        """
        indices = self._load_indices()
        return list(indices.values())

    def get_index(self, name: str) -> VectorIndexMetadata:
        """Get metadata for a named index.

        Args:
            name: Index name.

        Returns:
            VectorIndexMetadata for the index.

        Raises:
            NamedIndexNotFoundError: If index doesn't exist.
        """
        indices = self._load_indices()
        if name not in indices:
            raise NamedIndexNotFoundError(name)
        return indices[name]

    def index_exists(self, name: str) -> bool:
        """Check if an index exists.

        Args:
            name: Index name.

        Returns:
            True if index exists, False otherwise.
        """
        indices = self._load_indices()
        return name in indices

    def create_index(
        self,
        name: str,
        model_name: str,
        dimensions: int | None = None,
        chunk_size: int = 300,
        chunk_overlap: int = 50,
    ) -> VectorIndexMetadata:
        """Create a new named index.

        Args:
            name: Index name (e.g., "nova-1024").
            model_name: CLI model name (e.g., "nova", "titan-v2").
            dimensions: Embedding dimensions (None for model default).
            chunk_size: Words per chunk.
            chunk_overlap: Overlap words between chunks.

        Returns:
            Created VectorIndexMetadata.

        Raises:
            ValueError: If index already exists or model/dimensions invalid.
        """
        indices = self._load_indices()

        if name in indices:
            raise ValueError(
                f"Index '{name}' already exists. Delete it first or use a different name."
            )

        # Validate model and dimensions
        config = get_model_config(model_name)
        validated_dims = validate_dimensions(model_name, dimensions)

        # Create metadata
        metadata = VectorIndexMetadata(
            name=name,
            embedding_model=config.model_id,
            dimensions=validated_dims,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunk_count=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Create index directory
        index_dir = get_named_index_dir(name)
        index_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        self._save_index_metadata(name, metadata)

        # Update registry
        indices[name] = metadata
        self._save_indices()

        logger.info(
            "Created vector index '%s' with model %s (%d dims)", name, model_name, validated_dims
        )
        return metadata

    def _save_index_metadata(self, name: str, metadata: VectorIndexMetadata) -> None:
        """Save metadata for a specific index.

        Args:
            name: Index name.
            metadata: VectorIndexMetadata to save.
        """
        metadata_path = get_named_index_metadata_path(name)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        data = metadata.model_dump()
        # Convert datetime to ISO format strings
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].isoformat()
        if isinstance(data.get("updated_at"), datetime):
            data["updated_at"] = data["updated_at"].isoformat()

        with open(metadata_path, "w") as f:
            json.dump(data, f, indent=2)

    def delete_index(self, name: str) -> None:
        """Delete a named index.

        Args:
            name: Index name.

        Raises:
            NamedIndexNotFoundError: If index doesn't exist.
        """
        indices = self._load_indices()

        if name not in indices:
            raise NamedIndexNotFoundError(name)

        # Remove index directory
        index_dir = get_named_index_dir(name)
        if index_dir.exists():
            import shutil

            shutil.rmtree(index_dir)

        # Update registry
        del indices[name]
        self._save_indices()

        logger.info("Deleted vector index '%s'", name)

    def update_index_stats(
        self,
        name: str,
        chunk_count: int,
        total_tokens: int,
        estimated_cost_usd: float,
    ) -> VectorIndexMetadata:
        """Update statistics for an index.

        Args:
            name: Index name.
            chunk_count: Total chunks in index.
            total_tokens: Total tokens processed.
            estimated_cost_usd: Estimated cost.

        Returns:
            Updated VectorIndexMetadata.
        """
        indices = self._load_indices()

        if name not in indices:
            raise NamedIndexNotFoundError(name)

        metadata = indices[name]
        # Create new metadata with updated values
        updated_metadata = VectorIndexMetadata(
            name=metadata.name,
            embedding_model=metadata.embedding_model,
            dimensions=metadata.dimensions,
            chunk_size=metadata.chunk_size,
            chunk_overlap=metadata.chunk_overlap,
            chunk_count=chunk_count,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            created_at=metadata.created_at,
            updated_at=datetime.now(),
        )

        indices[name] = updated_metadata
        self._save_index_metadata(name, updated_metadata)
        self._save_indices()

        return updated_metadata

    def get_model_name_for_index(self, name: str) -> str:
        """Get the CLI model name for an index.

        Args:
            name: Index name.

        Returns:
            CLI model name (e.g., "nova", "titan-v2").
        """
        from paper_index_tool.vector.embeddings import EMBEDDING_MODELS

        metadata = self.get_index(name)

        # Reverse lookup: find CLI name from model ID
        for model_name, config in EMBEDDING_MODELS.items():
            if config.model_id == metadata.embedding_model:
                return model_name

        # Fallback to the model ID if not found
        return metadata.embedding_model

    def load_index_data(self, name: str) -> tuple[Any, list[Chunk]]:
        """Load FAISS index and chunks for a named index.

        Args:
            name: Index name.

        Returns:
            Tuple of (FAISS index, list of Chunks).

        Raises:
            NamedIndexNotFoundError: If index or data doesn't exist.
        """
        if not self.index_exists(name):
            raise NamedIndexNotFoundError(name)

        faiss_path = get_named_index_faiss_path(name)
        chunks_path = get_named_index_chunks_path(name)

        if not faiss_path.exists() or not chunks_path.exists():
            raise NamedIndexNotFoundError(name)

        try:
            import faiss  # type: ignore[import-not-found]

            index = faiss.read_index(str(faiss_path))

            with open(chunks_path) as f:
                chunks_data = json.load(f)
            chunks = [Chunk.from_dict(d) for d in chunks_data]

            logger.debug("Loaded index '%s' with %d chunks", name, len(chunks))
            return index, chunks
        except ImportError:
            raise ImportError(
                "faiss-cpu is required for vector search. "
                "Install with: pip install paper-index-tool[vector] "
                "or: uv sync --extra vector"
            )
        except Exception as e:
            logger.error("Failed to load index '%s': %s", name, e)
            raise NamedIndexNotFoundError(name) from e

    def save_index_data(self, name: str, index: Any, chunks: list[Chunk]) -> None:
        """Save FAISS index and chunks for a named index.

        Args:
            name: Index name.
            index: FAISS index object.
            chunks: List of Chunk objects.
        """
        try:
            import faiss

            index_dir = get_named_index_dir(name)
            index_dir.mkdir(parents=True, exist_ok=True)

            faiss_path = get_named_index_faiss_path(name)
            chunks_path = get_named_index_chunks_path(name)

            faiss.write_index(index, str(faiss_path))

            chunks_data = [chunk.to_dict() for chunk in chunks]
            with open(chunks_path, "w") as f:
                json.dump(chunks_data, f, indent=2)

            logger.debug("Saved index '%s' with %d chunks", name, len(chunks))
        except ImportError:
            raise ImportError(
                "faiss-cpu is required for vector search. "
                "Install with: pip install paper-index-tool[vector] "
                "or: uv sync --extra vector"
            )

    def add_entry_to_index(
        self,
        name: str,
        entry_id: str,
        entry_type: str,
        searchable_text: str,
    ) -> dict[str, int | float]:
        """Add a single entry to an existing named index.

        Chunks the entry, generates embeddings, and adds them to the
        FAISS index. More efficient than rebuilding the entire index.

        Args:
            name: Index name.
            entry_id: ID of the entry (paper, book, or media).
            entry_type: Type of entry ("paper", "book", or "media").
            searchable_text: Full searchable text of the entry.

        Returns:
            Dictionary with stats: {"chunks": N, "tokens": T, "cost": $}

        Raises:
            NamedIndexNotFoundError: If index doesn't exist.
        """
        from paper_index_tool.vector.chunking import TextChunker
        from paper_index_tool.vector.embeddings import BedrockEmbeddings

        try:
            import faiss
            import numpy as np
        except ImportError:
            raise ImportError(
                "faiss-cpu and numpy are required for vector search. "
                "Install with: pip install paper-index-tool[vector] "
                "or: uv sync --extra vector"
            )

        if not self.index_exists(name):
            raise NamedIndexNotFoundError(name)

        # Load existing index and chunks
        index, chunks = self.load_index_data(name)
        metadata = self.get_index(name)
        model_name = self.get_model_name_for_index(name)

        # Chunk the new entry
        chunker = TextChunker(
            chunk_size=metadata.chunk_size,
            overlap=metadata.chunk_overlap,
        )
        new_chunks = chunker.chunk_text(searchable_text, entry_id, entry_type)

        if not new_chunks:
            logger.debug("No chunks generated for entry %s", entry_id)
            return {"chunks": 0, "tokens": 0, "cost": 0.0}

        # Generate embeddings for new chunks
        embeddings_client = BedrockEmbeddings(
            model_name=model_name,
            dimensions=metadata.dimensions,
        )
        texts = [chunk.text for chunk in new_chunks]
        embeddings_list, stats = embeddings_client.embed_texts(texts, show_progress=False)

        # Add to FAISS index
        embeddings_array = np.array(embeddings_list, dtype=np.float32)
        faiss.normalize_L2(embeddings_array)
        index.add(embeddings_array)

        # Update chunks list
        chunks.extend(new_chunks)

        # Save updated index and chunks
        self.save_index_data(name, index, chunks)

        # Update metadata stats
        self.update_index_stats(
            name,
            chunk_count=len(chunks),
            total_tokens=metadata.total_tokens + stats.total_tokens,
            estimated_cost_usd=metadata.estimated_cost_usd + stats.total_cost,
        )

        logger.info(
            "Added %d chunks for %s '%s' to index '%s'",
            len(new_chunks),
            entry_type,
            entry_id,
            name,
        )

        return {
            "chunks": len(new_chunks),
            "tokens": stats.total_tokens,
            "cost": stats.total_cost,
        }

    def remove_entry_from_index(self, name: str, entry_id: str) -> int:
        """Remove an entry from a named index.

        Removes all chunks associated with an entry ID from the index.
        Note: This requires rebuilding the FAISS index as IndexFlatIP
        doesn't support removal.

        Args:
            name: Index name.
            entry_id: ID of the entry to remove.

        Returns:
            Number of chunks removed.

        Raises:
            NamedIndexNotFoundError: If index doesn't exist.
        """
        from paper_index_tool.vector.embeddings import BedrockEmbeddings

        try:
            import faiss
            import numpy as np
        except ImportError:
            raise ImportError(
                "faiss-cpu and numpy are required for vector search. "
                "Install with: pip install paper-index-tool[vector] "
                "or: uv sync --extra vector"
            )

        if not self.index_exists(name):
            raise NamedIndexNotFoundError(name)

        # Load existing index and chunks
        _old_index, chunks = self.load_index_data(name)
        metadata = self.get_index(name)
        model_name = self.get_model_name_for_index(name)

        # Filter out chunks belonging to the entry
        original_count = len(chunks)
        remaining_chunks = [c for c in chunks if c.entry_id != entry_id]
        removed_count = original_count - len(remaining_chunks)

        if removed_count == 0:
            logger.debug("No chunks found for entry %s in index '%s'", entry_id, name)
            return 0

        # Rebuild FAISS index with remaining chunks only
        if remaining_chunks:
            embeddings_client = BedrockEmbeddings(
                model_name=model_name,
                dimensions=metadata.dimensions,
            )
            texts = [chunk.text for chunk in remaining_chunks]
            embeddings_list, _stats = embeddings_client.embed_texts(texts, show_progress=False)

            embeddings_array = np.array(embeddings_list, dtype=np.float32)
            faiss.normalize_L2(embeddings_array)

            new_index = faiss.IndexFlatIP(metadata.dimensions)
            new_index.add(embeddings_array)

            self.save_index_data(name, new_index, remaining_chunks)
        else:
            # No chunks left - create empty index
            new_index = faiss.IndexFlatIP(metadata.dimensions)
            self.save_index_data(name, new_index, [])

        # Update metadata
        self.update_index_stats(
            name,
            chunk_count=len(remaining_chunks),
            total_tokens=metadata.total_tokens,  # Can't easily track removal
            estimated_cost_usd=metadata.estimated_cost_usd,  # Can't easily track removal
        )

        logger.info("Removed %d chunks for '%s' from index '%s'", removed_count, entry_id, name)
        return removed_count


def update_all_indices_with_entry(
    entry_id: str,
    entry_type: str,
    searchable_text: str,
) -> dict[str, dict[str, Any]]:
    """Update all vector indices with a new entry.

    Adds the entry to all existing vector indices. Called when a new
    paper, book, or media is created.

    Args:
        entry_id: ID of the entry.
        entry_type: Type ("paper", "book", or "media").
        searchable_text: Full searchable text of the entry.

    Returns:
        Dictionary mapping index names to their stats (or error info).
    """
    registry = VectorIndexRegistry()
    indices = registry.list_indices()
    results: dict[str, dict[str, Any]] = {}

    for index_meta in indices:
        try:
            stats = registry.add_entry_to_index(
                name=index_meta.name,
                entry_id=entry_id,
                entry_type=entry_type,
                searchable_text=searchable_text,
            )
            results[index_meta.name] = stats
        except Exception as e:
            logger.warning(
                "Failed to update index '%s' with entry '%s': %s", index_meta.name, entry_id, e
            )
            results[index_meta.name] = {"error": str(e)}

    return results


def remove_entry_from_all_indices(entry_id: str) -> dict[str, int]:
    """Remove an entry from all vector indices.

    Removes all chunks associated with an entry ID from all indices.
    Called when a paper, book, or media is deleted.

    Args:
        entry_id: ID of the entry to remove.

    Returns:
        Dictionary mapping index names to removed chunk counts.
    """
    registry = VectorIndexRegistry()
    indices = registry.list_indices()
    results: dict[str, int] = {}

    for index_meta in indices:
        try:
            removed = registry.remove_entry_from_index(index_meta.name, entry_id)
            results[index_meta.name] = removed
        except Exception as e:
            logger.warning("Failed to remove from index '%s': %s", index_meta.name, e)
            results[index_meta.name] = -1  # Indicate error

    return results
