"""Path management for paper-index-tool.

This module provides centralized path configuration for all storage locations
used by paper-index-tool. All paths are relative to the user's home directory
under ~/.config/paper-index-tool/.

Functions:
    get_config_dir: Get the main configuration directory.
    get_papers_path: Get the path to papers.json registry file.
    get_books_path: Get the path to books.json registry file.
    get_media_path: Get the path to media.json registry file.
    get_bm25_index_dir: Get the directory for BM25 search index files.
    ensure_config_dir: Create all required directories if they don't exist.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from pathlib import Path


def get_config_dir() -> Path:
    """Get the configuration directory for paper-index-tool.

    The configuration directory stores all persistent data including
    paper/book registries and search indices.

    Returns:
        Path to ~/.config/paper-index-tool/

    Example:
        >>> config_dir = get_config_dir()
        >>> str(config_dir).endswith(".config/paper-index-tool")
        True
    """
    return Path.home() / ".config" / "paper-index-tool"


def get_papers_path() -> Path:
    """Get the path to the papers registry file.

    The papers registry stores all academic paper entries with their
    metadata and content fields in JSON format.

    Returns:
        Path to ~/.config/paper-index-tool/papers.json

    Example:
        >>> papers_path = get_papers_path()
        >>> papers_path.name
        'papers.json'
    """
    return get_config_dir() / "papers.json"


def get_books_path() -> Path:
    """Get the path to the books registry file.

    The books registry stores all book/chapter entries with their
    metadata and content fields in JSON format.

    Returns:
        Path to ~/.config/paper-index-tool/books.json

    Example:
        >>> books_path = get_books_path()
        >>> books_path.name
        'books.json'
    """
    return get_config_dir() / "books.json"


def get_media_path() -> Path:
    """Get the path to the media registry file.

    The media registry stores all media entries (video, podcast, blog)
    with their metadata and content fields in JSON format.

    Returns:
        Path to ~/.config/paper-index-tool/media.json

    Example:
        >>> media_path = get_media_path()
        >>> media_path.name
        'media.json'
    """
    return get_config_dir() / "media.json"


def get_bm25_index_dir() -> Path:
    """Get the directory for BM25 index files.

    The BM25 index directory stores the search index files used
    for full-text search across papers and books.

    Returns:
        Path to ~/.config/paper-index-tool/bm25s/

    Example:
        >>> bm25_dir = get_bm25_index_dir()
        >>> bm25_dir.name
        'bm25s'
    """
    return get_config_dir() / "bm25s"


def get_vector_index_dir() -> Path:
    """Get the directory for vector index files.

    The vector index directory stores FAISS index files and chunk
    metadata for semantic search across papers, books, and media.

    Returns:
        Path to ~/.config/paper-index-tool/vectors/

    Example:
        >>> vector_dir = get_vector_index_dir()
        >>> vector_dir.name
        'vectors'
    """
    return get_config_dir() / "vectors"


def get_chunks_path() -> Path:
    """Get the path to the chunks metadata file.

    The chunks file stores text chunks with their embeddings metadata
    for vector search.

    Returns:
        Path to ~/.config/paper-index-tool/vectors/chunks.json

    Example:
        >>> chunks_path = get_chunks_path()
        >>> chunks_path.name
        'chunks.json'
    """
    return get_vector_index_dir() / "chunks.json"


def get_faiss_index_path() -> Path:
    """Get the path to the FAISS index file (legacy single-index).

    Returns:
        Path to ~/.config/paper-index-tool/vectors/index.faiss

    Example:
        >>> faiss_path = get_faiss_index_path()
        >>> faiss_path.name
        'index.faiss'
    """
    return get_vector_index_dir() / "index.faiss"


def get_named_index_dir(name: str) -> Path:
    """Get the directory for a named vector index.

    Each named index has its own directory containing the FAISS index,
    chunks metadata, and index configuration.

    Args:
        name: Index name (e.g., "nova-1024", "titan-v2").

    Returns:
        Path to ~/.config/paper-index-tool/vectors/<name>/

    Example:
        >>> index_dir = get_named_index_dir("nova-1024")
        >>> index_dir.name
        'nova-1024'
    """
    return get_vector_index_dir() / name


def get_named_index_faiss_path(name: str) -> Path:
    """Get the FAISS index file path for a named index.

    Args:
        name: Index name.

    Returns:
        Path to ~/.config/paper-index-tool/vectors/<name>/index.faiss
    """
    return get_named_index_dir(name) / "index.faiss"


def get_named_index_chunks_path(name: str) -> Path:
    """Get the chunks metadata file path for a named index.

    Args:
        name: Index name.

    Returns:
        Path to ~/.config/paper-index-tool/vectors/<name>/chunks.json
    """
    return get_named_index_dir(name) / "chunks.json"


def get_named_index_metadata_path(name: str) -> Path:
    """Get the metadata file path for a named index.

    Args:
        name: Index name.

    Returns:
        Path to ~/.config/paper-index-tool/vectors/<name>/metadata.json
    """
    return get_named_index_dir(name) / "metadata.json"


def get_vector_indices_path() -> Path:
    """Get the path to the vector indices registry file.

    The indices registry tracks all named vector indices and their
    configurations.

    Returns:
        Path to ~/.config/paper-index-tool/vectors/indices.json

    Example:
        >>> indices_path = get_vector_indices_path()
        >>> indices_path.name
        'indices.json'
    """
    return get_vector_index_dir() / "indices.json"


def get_settings_path() -> Path:
    """Get the path to the global settings file.

    The settings file stores user preferences like the default
    vector index for semantic search.

    Returns:
        Path to ~/.config/paper-index-tool/settings.json

    Example:
        >>> settings_path = get_settings_path()
        >>> settings_path.name
        'settings.json'
    """
    return get_config_dir() / "settings.json"


def ensure_config_dir() -> None:
    """Create configuration directories if they don't exist.

    Creates all required directories for paper-index-tool storage:
        - ~/.config/paper-index-tool/ (main config directory)
        - ~/.config/paper-index-tool/bm25s/ (search index directory)
        - ~/.config/paper-index-tool/vectors/ (vector index directory)

    This function is idempotent and safe to call multiple times.

    Example:
        >>> ensure_config_dir()
        >>> get_config_dir().exists()
        True
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    bm25_dir = get_bm25_index_dir()
    bm25_dir.mkdir(parents=True, exist_ok=True)

    vector_dir = get_vector_index_dir()
    vector_dir.mkdir(parents=True, exist_ok=True)
