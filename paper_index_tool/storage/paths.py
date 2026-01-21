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


def ensure_config_dir() -> None:
    """Create configuration directories if they don't exist.

    Creates all required directories for paper-index-tool storage:
        - ~/.config/paper-index-tool/ (main config directory)
        - ~/.config/paper-index-tool/bm25s/ (search index directory)

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
