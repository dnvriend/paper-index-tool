"""Settings management for paper-index-tool.

This module provides functions for managing global application settings
that persist across CLI sessions.

Functions:
    load_settings: Load settings from disk.
    save_settings: Save settings to disk.
    get_default_vector_index: Get the default vector index name.
    set_default_vector_index: Set the default vector index name.
    clear_default_vector_index: Clear the default vector index setting.
"""

from __future__ import annotations

import json

from paper_index_tool.logging_config import get_logger
from paper_index_tool.models import Settings
from paper_index_tool.storage.paths import get_settings_path

logger = get_logger(__name__)


def load_settings() -> Settings:
    """Load settings from disk.

    Returns:
        Settings object. Returns default settings if file doesn't exist.

    Example:
        >>> settings = load_settings()
        >>> print(settings.default_vector_index)
    """
    settings_path = get_settings_path()

    if not settings_path.exists():
        return Settings()

    try:
        with open(settings_path) as f:
            data = json.load(f)
        return Settings(**data)
    except Exception as e:
        logger.warning("Failed to load settings: %s", e)
        return Settings()


def save_settings(settings: Settings) -> None:
    """Save settings to disk.

    Args:
        settings: Settings object to save.

    Example:
        >>> settings = Settings(default_vector_index="nova-1024")
        >>> save_settings(settings)
    """
    settings_path = get_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    data = settings.model_dump()

    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.debug("Saved settings to %s", settings_path)


def get_default_vector_index() -> str | None:
    """Get the default vector index name.

    Returns:
        Default index name or None if not set.

    Example:
        >>> default = get_default_vector_index()
        >>> if default:
        ...     print(f"Default index: {default}")
    """
    settings = load_settings()
    return settings.default_vector_index


def set_default_vector_index(index_name: str) -> None:
    """Set the default vector index name.

    Args:
        index_name: Name of the index to set as default.

    Example:
        >>> set_default_vector_index("nova-1024")
    """
    settings = load_settings()
    settings.default_vector_index = index_name
    save_settings(settings)
    logger.info("Set default vector index to '%s'", index_name)


def clear_default_vector_index() -> None:
    """Clear the default vector index setting.

    Example:
        >>> clear_default_vector_index()
    """
    settings = load_settings()
    settings.default_vector_index = None
    save_settings(settings)
    logger.info("Cleared default vector index")
