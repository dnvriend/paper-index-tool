"""Storage module for paper-index-tool.

This module provides storage functionality for academic papers, books, and media,
including JSON-based registries and path management utilities.

Classes:
    PaperRegistry: Registry for academic papers (papers.json).
    BookRegistry: Registry for books and book chapters (books.json).
    MediaRegistry: Registry for media sources (media.json).
    BaseRegistry: Abstract base class for registry implementations.

Exceptions:
    RegistryError: Base exception for registry operations.
    EntryNotFoundError: Raised when an entry is not found.
    EntryExistsError: Raised when an entry already exists.
    RegistryCorruptedError: Raised when a registry file is corrupted.

Functions:
    get_config_dir: Get the main configuration directory.
    get_papers_path: Get the path to papers.json.
    get_books_path: Get the path to books.json.
    get_media_path: Get the path to media.json.
    get_bm25_index_dir: Get the BM25 search index directory.
    get_vector_index_dir: Get the vector search index directory.
    get_chunks_path: Get the path to chunks.json.
    get_faiss_index_path: Get the path to the FAISS index.
    ensure_config_dir: Create all required directories.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from paper_index_tool.storage.paths import (
    ensure_config_dir,
    get_bm25_index_dir,
    get_books_path,
    get_chunks_path,
    get_config_dir,
    get_faiss_index_path,
    get_media_path,
    get_papers_path,
    get_vector_index_dir,
)
from paper_index_tool.storage.registry import (
    BaseRegistry,
    BookRegistry,
    EntryExistsError,
    EntryNotFoundError,
    MediaRegistry,
    PaperRegistry,
    RegistryCorruptedError,
    RegistryError,
)

__all__ = [
    # Registries
    "BaseRegistry",
    "BookRegistry",
    "MediaRegistry",
    "PaperRegistry",
    # Exceptions
    "EntryExistsError",
    "EntryNotFoundError",
    "RegistryCorruptedError",
    "RegistryError",
    # Path functions
    "ensure_config_dir",
    "get_bm25_index_dir",
    "get_books_path",
    "get_chunks_path",
    "get_config_dir",
    "get_faiss_index_path",
    "get_media_path",
    "get_papers_path",
    "get_vector_index_dir",
]
