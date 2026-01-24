"""Registry management for paper-index-tool.

This module provides registry classes for managing academic papers, books, and media.
All registries share common functionality through the BaseRegistry abstract
base class, following SOLID principles (OCP, DIP, SRP).

Classes:
    BaseRegistry: Abstract base class for registry implementations.
    PaperRegistry: Manages the paper registry (papers.json).
    BookRegistry: Manages the book registry (books.json).
    MediaRegistry: Manages the media registry (media.json).

Type Variables:
    T: Generic type bound to Pydantic BaseModel (Paper, Book, or Media).

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import cast

from pydantic import BaseModel

from paper_index_tool.logging_config import get_logger
from paper_index_tool.models import Book, Media, Paper
from paper_index_tool.storage.paths import (
    ensure_config_dir,
    get_books_path,
    get_media_path,
    get_papers_path,
)

logger = get_logger(__name__)


class RegistryError(Exception):
    """Base exception for registry operations.

    Provides agent-friendly error messages with context and suggested actions.

    Attributes:
        message: Human-readable error description.
        entity_type: Type of entity (paper/book) involved.
        entity_id: ID of the entity involved (if applicable).

    Example:
        >>> raise RegistryError("Paper not found", "paper", "ashford2012")
    """

    def __init__(
        self,
        message: str,
        entity_type: str = "entry",
        entity_id: str | None = None,
    ) -> None:
        """Initialize RegistryError with context.

        Args:
            message: Error description.
            entity_type: Type of entity involved.
            entity_id: ID of entity involved.
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(message)


class EntryNotFoundError(RegistryError):
    """Raised when an entry is not found in the registry.

    Provides actionable guidance for resolving the missing entry.

    Example:
        >>> raise EntryNotFoundError("paper", "ashford2012")
    """

    def __init__(self, entity_type: str, entity_id: str) -> None:
        """Initialize EntryNotFoundError.

        Args:
            entity_type: Type of entry (paper/book).
            entity_id: ID that was not found.
        """
        message = (
            f"{entity_type.capitalize()} '{entity_id}' not found in registry. "
            f"Available actions: "
            f"1) Check the ID spelling (use 'list' command to see all {entity_type}s). "
            f"2) Create a new {entity_type} with 'create {entity_id}' command."
        )
        super().__init__(message, entity_type, entity_id)


class EntryExistsError(RegistryError):
    """Raised when attempting to create an entry that already exists.

    Provides guidance on updating existing entries instead.

    Example:
        >>> raise EntryExistsError("paper", "ashford2012")
    """

    def __init__(self, entity_type: str, entity_id: str) -> None:
        """Initialize EntryExistsError.

        Args:
            entity_type: Type of entry (paper/book).
            entity_id: ID that already exists.
        """
        message = (
            f"{entity_type.capitalize()} '{entity_id}' already exists in registry. "
            f"Available actions: "
            f"1) Use 'update {entity_id}' to modify existing {entity_type}. "
            f"2) Use 'delete {entity_id}' first to replace it. "
            f"3) Choose a different ID (e.g., '{entity_id}a' or '{entity_id}b')."
        )
        super().__init__(message, entity_type, entity_id)


class RegistryCorruptedError(RegistryError):
    """Raised when the registry file is corrupted or unreadable.

    Provides recovery guidance for corrupted registry files.

    Example:
        >>> raise RegistryCorruptedError("paper", "/path/to/papers.json", parse_error)
    """

    def __init__(self, entity_type: str, file_path: Path, original_error: Exception) -> None:
        """Initialize RegistryCorruptedError.

        Args:
            entity_type: Type of registry (paper/book).
            file_path: Path to the corrupted file.
            original_error: Original exception that was raised.
        """
        message = (
            f"{entity_type.capitalize()} registry file is corrupted: {file_path}. "
            f"Error: {original_error}. "
            f"Recovery options: "
            f"1) Delete the file and rebuild from backups. "
            f"2) Manually fix the JSON syntax error. "
            f"3) Restore from a backup if available."
        )
        super().__init__(message, entity_type)


class BaseRegistry[T: BaseModel](ABC):
    """Abstract base class for registry implementations.

    Provides common CRUD operations, import/export functionality, and
    searchable content retrieval. Subclasses must implement the abstract
    properties to specify the model type, entity name, and registry path.

    This class follows SOLID principles:
        - SRP: Only handles registry persistence logic.
        - OCP: Extensible via subclassing without modification.
        - LSP: Subclasses (PaperRegistry, BookRegistry) are interchangeable.
        - ISP: Small, focused interface for registry operations.
        - DIP: Depends on abstractions (T, Path) not concretions.

    Type Parameters:
        T: Pydantic model type (Paper or Book).

    Abstract Properties:
        model_class: The Pydantic model class for validation.
        entity_name: Human-readable name (paper/book) for error messages.
        registry_path: Path to the JSON registry file.

    Methods:
        list_entries: List all entries sorted by ID.
        add_entry: Add a new entry to the registry.
        update_entry: Update an existing entry.
        delete_entry: Delete an entry from the registry.
        get_entry: Get a single entry by ID.
        entry_exists: Check if an entry exists.
        get_all_searchable_content: Get searchable text for all entries.
        export_all: Export all entries as a dictionary.
        import_all: Import entries from a dictionary.
        count: Get the number of entries in the registry.

    Example:
        >>> class PaperRegistry(BaseRegistry[Paper]):
        ...     @property
        ...     def model_class(self) -> type[Paper]:
        ...         return Paper
    """

    def __init__(self) -> None:
        """Initialize the registry.

        Creates the configuration directory and registry file if they
        don't exist. Safe to call multiple times.
        """
        ensure_config_dir()
        self._ensure_registry()

    @property
    @abstractmethod
    def model_class(self) -> type[T]:
        """Get the Pydantic model class for this registry.

        Returns:
            The model class (Paper or Book) used for validation.
        """
        ...

    @property
    @abstractmethod
    def entity_name(self) -> str:
        """Get the human-readable entity name.

        Returns:
            Entity name (paper/book) for use in error messages and logging.
        """
        ...

    @property
    @abstractmethod
    def registry_path(self) -> Path:
        """Get the path to the registry JSON file.

        Returns:
            Path to the registry file (papers.json or books.json).
        """
        ...

    def _ensure_registry(self) -> None:
        """Create registry file if it doesn't exist.

        Creates an empty JSON object {} as the initial registry content.
        This is idempotent and safe to call multiple times.
        """
        if not self.registry_path.exists():
            logger.debug(
                "Creating new %s registry file at %s",
                self.entity_name,
                self.registry_path,
            )
            self._save_registry({})

    def _load_registry(self) -> dict[str, dict[str, object]]:
        """Load the registry from disk.

        Reads and parses the JSON registry file. Returns an empty dict
        if the file is missing or corrupted (with a warning logged).

        Returns:
            Dictionary mapping entry IDs to entry data dictionaries.

        Raises:
            RegistryCorruptedError: If JSON parsing fails and recovery is needed.

        Example:
            >>> registry = self._load_registry()
            >>> len(registry)
            5
        """
        try:
            with open(self.registry_path) as f:
                data: dict[str, dict[str, object]] = json.load(f)
                logger.debug(
                    "Loaded %s registry with %d entries",
                    self.entity_name,
                    len(data),
                )
                return data
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse %s registry: %s",
                self.entity_name,
                e,
            )
            raise RegistryCorruptedError(self.entity_name, self.registry_path, e)
        except FileNotFoundError:
            logger.warning(
                "%s registry not found at %s. Creating new registry.",
                self.entity_name.capitalize(),
                self.registry_path,
            )
            return {}

    def _save_registry(self, data: dict[str, dict[str, object]]) -> None:
        """Save the registry to disk.

        Writes the registry data to JSON with pretty-printing (indent=2).
        Datetime objects are automatically converted to ISO format strings.

        Args:
            data: Registry data dictionary to save.

        Example:
            >>> self._save_registry({"ashford2012": {...}})
        """
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.debug(
            "Saved %s registry with %d entries",
            self.entity_name,
            len(data),
        )

    def list_entries(self) -> list[T]:
        """List all entries sorted by ID.

        Retrieves all entries from the registry, validates them against
        the model class, and returns them sorted alphabetically by ID.

        Returns:
            List of validated model objects sorted by ID.

        Example:
            >>> papers = paper_registry.list_entries()
            >>> [p.id for p in papers]
            ['ashford2012', 'brown2015', 'smith2020']
        """
        registry = self._load_registry()
        entries = []
        for entry_id in sorted(registry.keys()):
            entry_data = registry[entry_id]
            entry = self.model_class.model_validate(entry_data)
            entries.append(entry)
        logger.debug("Found %d %ss", len(entries), self.entity_name)
        return entries

    def add_entry(self, entry: T) -> None:
        """Add a new entry to the registry.

        Validates the entry doesn't already exist, then adds it to the
        registry. The entry is serialized to JSON-compatible format.

        Args:
            entry: Model object to add (must have 'id' attribute).

        Raises:
            EntryExistsError: If entry ID already exists in registry.

        Example:
            >>> paper = Paper(id="ashford2012", ...)
            >>> paper_registry.add_entry(paper)
        """
        registry = self._load_registry()
        entry_id = getattr(entry, "id")
        if entry_id in registry:
            raise EntryExistsError(self.entity_name, entry_id)
        registry[entry_id] = entry.model_dump(mode="json")
        self._save_registry(registry)
        logger.info("Added %s '%s' to registry", self.entity_name, entry_id)

    def update_entry(self, entry_id: str, updates: dict[str, object]) -> T:
        """Update an existing entry.

        Applies partial updates to an existing entry. Only non-None values
        in the updates dict are applied. The updated_at timestamp is
        automatically set to the current time.

        Args:
            entry_id: ID of entry to update.
            updates: Dictionary of field updates (None values are skipped).

        Returns:
            Updated and validated model object.

        Raises:
            EntryNotFoundError: If entry ID not found in registry.

        Example:
            >>> updated = paper_registry.update_entry(
            ...     "ashford2012",
            ...     {"rating": 5, "method": "Qualitative interviews"}
            ... )
            >>> updated.rating
            5
        """
        registry = self._load_registry()
        if entry_id not in registry:
            raise EntryNotFoundError(self.entity_name, entry_id)

        entry_data = registry[entry_id]
        # Apply updates (only non-None values)
        for key, value in updates.items():
            if value is not None:
                entry_data[key] = value
        entry_data["updated_at"] = datetime.now().isoformat()

        # Validate and save
        entry = self.model_class.model_validate(entry_data)
        registry[entry_id] = entry.model_dump(mode="json")
        self._save_registry(registry)
        logger.info("Updated %s '%s'", self.entity_name, entry_id)
        return entry

    def delete_entry(self, entry_id: str) -> None:
        """Delete an entry from the registry.

        Permanently removes an entry from the registry. This operation
        cannot be undone without a backup.

        Args:
            entry_id: ID of entry to delete.

        Raises:
            EntryNotFoundError: If entry ID not found in registry.

        Example:
            >>> paper_registry.delete_entry("ashford2012")
        """
        registry = self._load_registry()
        if entry_id not in registry:
            raise EntryNotFoundError(self.entity_name, entry_id)
        del registry[entry_id]
        self._save_registry(registry)
        logger.info("Deleted %s '%s'", self.entity_name, entry_id)

    def get_entry(self, entry_id: str) -> T | None:
        """Get an entry by ID.

        Retrieves and validates a single entry from the registry.
        Returns None if the entry doesn't exist (no exception raised).

        Args:
            entry_id: Entry ID to look up.

        Returns:
            Validated model object or None if not found.

        Example:
            >>> paper = paper_registry.get_entry("ashford2012")
            >>> paper.title if paper else "Not found"
            'Developing as a leader'
        """
        registry = self._load_registry()
        entry_data = registry.get(entry_id)
        if entry_data:
            logger.debug("Found %s '%s'", self.entity_name, entry_id)
            return self.model_class.model_validate(entry_data)
        logger.debug("%s '%s' not found", self.entity_name.capitalize(), entry_id)
        return None

    def entry_exists(self, entry_id: str) -> bool:
        """Check if an entry exists.

        Fast existence check without loading and validating the full entry.

        Args:
            entry_id: Entry ID to check.

        Returns:
            True if entry exists, False otherwise.

        Example:
            >>> paper_registry.entry_exists("ashford2012")
            True
        """
        registry = self._load_registry()
        exists = entry_id in registry
        logger.debug("%s '%s' exists: %s", self.entity_name.capitalize(), entry_id, exists)
        return exists

    def get_all_searchable_content(self) -> list[tuple[str, str]]:
        """Get searchable content for all entries.

        Extracts searchable text from all entries for BM25 indexing.
        Each entry must have a get_searchable_text() method.

        Returns:
            List of (entry_id, searchable_text) tuples.
            Only includes entries with non-empty searchable text.

        Example:
            >>> content = paper_registry.get_all_searchable_content()
            >>> [(id, text[:50]) for id, text in content[:2]]
            [('ashford2012', 'Leadership development...'), ...]
        """
        entries = self.list_entries()
        content = []
        for entry in entries:
            entry_id = cast(str, getattr(entry, "id"))
            # Both Paper and Book models have get_searchable_text method
            # Using hasattr check for type safety
            if hasattr(entry, "get_searchable_text"):
                get_text = getattr(entry, "get_searchable_text")
                text: str = get_text()
                if text:
                    content.append((entry_id, text))
        logger.debug(
            "Retrieved searchable content for %d %ss",
            len(content),
            self.entity_name,
        )
        return content

    def export_all(self) -> dict[str, dict[str, object]]:
        """Export all entries as a dictionary.

        Returns the raw registry data suitable for JSON export or backup.
        Entries are keyed by their ID.

        Returns:
            Dictionary mapping entry IDs to entry data dictionaries.

        Example:
            >>> export_data = paper_registry.export_all()
            >>> with open("backup.json", "w") as f:
            ...     json.dump(export_data, f, indent=2)
        """
        registry = self._load_registry()
        logger.info(
            "Exported %d %ss from registry",
            len(registry),
            self.entity_name,
        )
        return registry

    def import_all(self, data: dict[str, dict[str, object]], replace: bool = True) -> int:
        """Import entries from a dictionary.

        Imports entries from a dictionary (e.g., from JSON backup).
        Can either replace all existing entries or merge with existing data.

        Args:
            data: Dictionary mapping entry IDs to entry data.
            replace: If True, replace all existing entries. If False, merge
                     (existing entries are kept, new entries are added,
                     conflicting IDs are skipped with a warning).

        Returns:
            Number of entries imported.

        Raises:
            ValueError: If any entry fails validation.

        Example:
            >>> with open("backup.json") as f:
            ...     data = json.load(f)
            >>> count = paper_registry.import_all(data, replace=True)
            >>> print(f"Imported {count} papers")
            Imported 15 papers
        """
        # Validate all entries first
        validated_entries: dict[str, dict[str, object]] = {}
        for entry_id, entry_data in data.items():
            try:
                entry = self.model_class.model_validate(entry_data)
                validated_entries[entry_id] = entry.model_dump(mode="json")
            except Exception as e:
                raise ValueError(
                    f"Failed to validate {self.entity_name} '{entry_id}': {e}. "
                    f"Please check the data format and required fields."
                )

        if replace:
            # Replace entire registry
            self._save_registry(validated_entries)
            logger.info(
                "Replaced %s registry with %d imported entries",
                self.entity_name,
                len(validated_entries),
            )
            return len(validated_entries)
        else:
            # Merge with existing registry
            registry = self._load_registry()
            imported_count = 0
            skipped_count = 0
            for entry_id, entry_data in validated_entries.items():
                if entry_id in registry:
                    logger.warning(
                        "Skipping %s '%s': already exists in registry",
                        self.entity_name,
                        entry_id,
                    )
                    skipped_count += 1
                else:
                    registry[entry_id] = entry_data
                    imported_count += 1
            self._save_registry(registry)
            logger.info(
                "Merged %d %ss into registry (skipped %d existing)",
                imported_count,
                self.entity_name,
                skipped_count,
            )
            return imported_count

    def count(self) -> int:
        """Get the number of entries in the registry.

        Fast count without loading and validating all entries.

        Returns:
            Number of entries in the registry.

        Example:
            >>> paper_registry.count()
            15
        """
        registry = self._load_registry()
        return len(registry)

    def clear(self) -> int:
        """Clear all entries from the registry.

        Removes all entries from the registry file. This operation
        cannot be undone without a backup.

        Returns:
            Number of entries that were removed.

        Example:
            >>> count = paper_registry.clear()
            >>> print(f"Removed {count} papers")
            Removed 15 papers
        """
        registry = self._load_registry()
        count = len(registry)
        self._save_registry({})
        logger.info("Cleared %d %ss from registry", count, self.entity_name)
        return count

    def rename_entry(self, old_id: str, new_id: str) -> T:
        """Rename an entry by changing its ID.

        Validates the old ID exists, new ID doesn't exist, and new ID format
        is valid. Updates the entry's ID field and updated_at timestamp.

        Args:
            old_id: Current ID of the entry to rename.
            new_id: New ID for the entry.

        Returns:
            The renamed and validated model object.

        Raises:
            EntryNotFoundError: If old_id not found in registry.
            EntryExistsError: If new_id already exists in registry.
            ValueError: If new_id format is invalid.

        Example:
            >>> paper = paper_registry.rename_entry("test2024", "renamed2024")
            >>> paper.id
            'renamed2024'
        """
        # Validate new_id format (alphanumeric with optional underscores/hyphens)
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", new_id):
            raise ValueError(
                f"Invalid {self.entity_name} ID format: '{new_id}'. "
                f"ID must start with alphanumeric and contain only alphanumeric, "
                f"underscores, or hyphens."
            )

        registry = self._load_registry()

        if old_id not in registry:
            raise EntryNotFoundError(self.entity_name, old_id)

        if new_id in registry:
            raise EntryExistsError(self.entity_name, new_id)

        # Move entry to new ID
        entry_data = registry[old_id]
        entry_data["id"] = new_id
        entry_data["updated_at"] = datetime.now().isoformat()

        # Validate and save
        entry = self.model_class.model_validate(entry_data)
        registry[new_id] = entry.model_dump(mode="json")
        del registry[old_id]
        self._save_registry(registry)

        logger.info(
            "Renamed %s '%s' to '%s'",
            self.entity_name,
            old_id,
            new_id,
        )
        return entry


class PaperRegistry(BaseRegistry[Paper]):
    """Manages the paper registry (papers.json).

    Specialized registry for academic papers with all Paper model fields.
    Stores papers in ~/.config/paper-index-tool/papers.json.

    This class extends BaseRegistry with Paper-specific configuration:
        - model_class: Paper
        - entity_name: "paper"
        - registry_path: ~/.config/paper-index-tool/papers.json

    Inherited Methods:
        list_entries, add_entry, update_entry, delete_entry, get_entry,
        entry_exists, get_all_searchable_content, export_all, import_all, count

    Convenience Aliases:
        list_papers: Alias for list_entries.
        add_paper: Alias for add_entry.
        update_paper: Alias for update_entry.
        delete_paper: Alias for delete_entry.
        get_paper: Alias for get_entry.
        paper_exists: Alias for entry_exists.

    Example:
        >>> registry = PaperRegistry()
        >>> papers = registry.list_papers()
        >>> registry.add_paper(new_paper)
    """

    @property
    def model_class(self) -> type[Paper]:
        """Get the Paper model class.

        Returns:
            The Paper class for validation.
        """
        return Paper

    @property
    def entity_name(self) -> str:
        """Get the entity name for papers.

        Returns:
            The string "paper" for use in messages.
        """
        return "paper"

    @property
    def registry_path(self) -> Path:
        """Get the path to papers.json.

        Returns:
            Path to ~/.config/paper-index-tool/papers.json
        """
        return get_papers_path()

    # =========================================================================
    # Convenience Aliases (Backward Compatibility)
    # =========================================================================

    def list_papers(self) -> list[Paper]:
        """List all papers sorted by ID.

        Alias for list_entries() for backward compatibility and
        improved readability in paper-specific code.

        Returns:
            List of Paper objects sorted alphabetically by ID.
        """
        return self.list_entries()

    def add_paper(self, paper: Paper) -> None:
        """Add a new paper to the registry.

        Alias for add_entry() for backward compatibility.

        Args:
            paper: Paper to add.

        Raises:
            EntryExistsError: If paper ID already exists.
        """
        self.add_entry(paper)

    def update_paper(self, paper_id: str, updates: dict[str, object]) -> Paper:
        """Update an existing paper.

        Alias for update_entry() for backward compatibility.

        Args:
            paper_id: ID of paper to update.
            updates: Dictionary of field updates.

        Returns:
            Updated Paper object.

        Raises:
            EntryNotFoundError: If paper not found.
        """
        return self.update_entry(paper_id, updates)

    def delete_paper(self, paper_id: str) -> None:
        """Delete a paper from the registry.

        Alias for delete_entry() for backward compatibility.

        Args:
            paper_id: ID of paper to delete.

        Raises:
            EntryNotFoundError: If paper not found.
        """
        self.delete_entry(paper_id)

    def get_paper(self, paper_id: str) -> Paper | None:
        """Get a paper by ID.

        Alias for get_entry() for backward compatibility.

        Args:
            paper_id: Paper ID to look up.

        Returns:
            Paper object or None if not found.
        """
        return self.get_entry(paper_id)

    def paper_exists(self, paper_id: str) -> bool:
        """Check if a paper exists.

        Alias for entry_exists() for backward compatibility.

        Args:
            paper_id: Paper ID to check.

        Returns:
            True if paper exists, False otherwise.
        """
        return self.entry_exists(paper_id)

    def rename_paper(self, old_id: str, new_id: str) -> Paper:
        """Rename a paper by changing its ID.

        Alias for rename_entry() for backward compatibility.

        Args:
            old_id: Current paper ID.
            new_id: New paper ID.

        Returns:
            Renamed Paper object.

        Raises:
            EntryNotFoundError: If old_id not found.
            EntryExistsError: If new_id already exists.
            ValueError: If new_id format is invalid.
        """
        return self.rename_entry(old_id, new_id)


class BookRegistry(BaseRegistry[Book]):
    """Manages the book registry (books.json).

    Specialized registry for books and book chapters with all Book model fields.
    Stores books in ~/.config/paper-index-tool/books.json.

    This class extends BaseRegistry with Book-specific configuration:
        - model_class: Book
        - entity_name: "book"
        - registry_path: ~/.config/paper-index-tool/books.json

    Inherited Methods:
        list_entries, add_entry, update_entry, delete_entry, get_entry,
        entry_exists, get_all_searchable_content, export_all, import_all, count

    Convenience Aliases:
        list_books: Alias for list_entries.
        add_book: Alias for add_entry.
        update_book: Alias for update_entry.
        delete_book: Alias for delete_entry.
        get_book: Alias for get_entry.
        book_exists: Alias for entry_exists.

    Example:
        >>> registry = BookRegistry()
        >>> books = registry.list_books()
        >>> registry.add_book(new_book)
    """

    @property
    def model_class(self) -> type[Book]:
        """Get the Book model class.

        Returns:
            The Book class for validation.
        """
        return Book

    @property
    def entity_name(self) -> str:
        """Get the entity name for books.

        Returns:
            The string "book" for use in messages.
        """
        return "book"

    @property
    def registry_path(self) -> Path:
        """Get the path to books.json.

        Returns:
            Path to ~/.config/paper-index-tool/books.json
        """
        return get_books_path()

    # =========================================================================
    # Convenience Aliases (API Consistency)
    # =========================================================================

    def list_books(self) -> list[Book]:
        """List all books sorted by ID.

        Alias for list_entries() for improved readability
        in book-specific code.

        Returns:
            List of Book objects sorted alphabetically by ID.
        """
        return self.list_entries()

    def add_book(self, book: Book) -> None:
        """Add a new book to the registry.

        Alias for add_entry() for API consistency.

        Args:
            book: Book to add.

        Raises:
            EntryExistsError: If book ID already exists.
        """
        self.add_entry(book)

    def update_book(self, book_id: str, updates: dict[str, object]) -> Book:
        """Update an existing book.

        Alias for update_entry() for API consistency.

        Args:
            book_id: ID of book to update.
            updates: Dictionary of field updates.

        Returns:
            Updated Book object.

        Raises:
            EntryNotFoundError: If book not found.
        """
        return self.update_entry(book_id, updates)

    def delete_book(self, book_id: str) -> None:
        """Delete a book from the registry.

        Alias for delete_entry() for API consistency.

        Args:
            book_id: ID of book to delete.

        Raises:
            EntryNotFoundError: If book not found.
        """
        self.delete_entry(book_id)

    def get_book(self, book_id: str) -> Book | None:
        """Get a book by ID.

        Alias for get_entry() for API consistency.

        Args:
            book_id: Book ID to look up.

        Returns:
            Book object or None if not found.
        """
        return self.get_entry(book_id)

    def book_exists(self, book_id: str) -> bool:
        """Check if a book exists.

        Alias for entry_exists() for API consistency.

        Args:
            book_id: Book ID to check.

        Returns:
            True if book exists, False otherwise.
        """
        return self.entry_exists(book_id)

    def rename_book(self, old_id: str, new_id: str) -> Book:
        """Rename a book by changing its ID.

        Alias for rename_entry() for API consistency.

        Args:
            old_id: Current book ID.
            new_id: New book ID.

        Returns:
            Renamed Book object.

        Raises:
            EntryNotFoundError: If old_id not found.
            EntryExistsError: If new_id already exists.
            ValueError: If new_id format is invalid.
        """
        return self.rename_entry(old_id, new_id)

    # =========================================================================
    # Chapter Grouping Methods
    # =========================================================================

    @staticmethod
    def is_chapter_id(entry_id: str) -> bool:
        """Check if an ID has a ch<n> suffix indicating a chapter.

        Args:
            entry_id: The book ID to check.

        Returns:
            True if the ID ends with ch followed by digits (e.g., vogelgesang2023ch1).

        Example:
            >>> BookRegistry.is_chapter_id("vogelgesang2023ch1")
            True
            >>> BookRegistry.is_chapter_id("vogelgesang2023")
            False
        """
        return bool(re.search(r"ch\d+$", entry_id))

    @staticmethod
    def get_basename(entry_id: str) -> str:
        """Extract the basename from a chapter ID.

        Removes the ch<n> suffix to get the base book identifier.

        Args:
            entry_id: The chapter ID (e.g., vogelgesang2023ch1).

        Returns:
            The basename without chapter suffix (e.g., vogelgesang2023).

        Example:
            >>> BookRegistry.get_basename("vogelgesang2023ch1")
            'vogelgesang2023'
            >>> BookRegistry.get_basename("vogelgesang2023")
            'vogelgesang2023'
        """
        return re.sub(r"ch\d+$", "", entry_id)

    def find_chapters(self, basename: str) -> list[Book]:
        """Find all chapters matching a basename, sorted by chapter number.

        Searches for all books with IDs matching the pattern <basename>ch<n>
        and returns them sorted by chapter number.

        Args:
            basename: The base book ID without chapter suffix.

        Returns:
            List of Book objects sorted by chapter number.
            Empty list if no chapters found.

        Example:
            >>> chapters = registry.find_chapters("vogelgesang2023")
            >>> [c.id for c in chapters]
            ['vogelgesang2023ch1', 'vogelgesang2023ch2', ..., 'vogelgesang2023ch11']
        """
        pattern = re.compile(rf"^{re.escape(basename)}ch(\d+)$")
        chapters: list[tuple[int, Book]] = []
        for book in self.list_books():
            match = pattern.match(book.id)
            if match:
                chapter_num = int(match.group(1))
                chapters.append((chapter_num, book))
        sorted_chapters = sorted(chapters, key=lambda x: x[0])
        result = [book for _, book in sorted_chapters]
        logger.debug(
            "Found %d chapters for basename '%s'",
            len(result),
            basename,
        )
        return result

    def get_book_or_chapters(self, book_id: str) -> Book | list[Book] | None:
        """Get a single book or all chapters if basename given.

        This method provides smart lookup:
        1. First tries exact match for book_id
        2. If not found and book_id has no ch<n> suffix, searches for chapters

        Args:
            book_id: Book ID or basename to look up.

        Returns:
            - Single Book if exact match found
            - List of Books if chapters found for basename
            - None if nothing found

        Example:
            >>> # Exact match returns single book
            >>> result = registry.get_book_or_chapters("vogelgesang2023ch1")
            >>> isinstance(result, Book)
            True

            >>> # Basename returns list of chapters
            >>> result = registry.get_book_or_chapters("vogelgesang2023")
            >>> isinstance(result, list)
            True
        """
        # First try exact match
        book = self.get_book(book_id)
        if book is not None:
            return book

        # If not found and no ch<n> suffix, look for chapters
        if not self.is_chapter_id(book_id):
            chapters = self.find_chapters(book_id)
            if chapters:
                logger.info(
                    "Found %d chapters for basename '%s'",
                    len(chapters),
                    book_id,
                )
                return chapters

        return None

    def delete_chapters(self, basename: str) -> int:
        """Delete all chapters matching a basename.

        Args:
            basename: The base book ID without chapter suffix.

        Returns:
            Number of chapters deleted.

        Raises:
            EntryNotFoundError: If no chapters found for basename.

        Example:
            >>> count = registry.delete_chapters("vogelgesang2023")
            >>> print(f"Deleted {count} chapters")
            Deleted 11 chapters
        """
        chapters = self.find_chapters(basename)
        if not chapters:
            raise EntryNotFoundError("book", basename)

        for chapter in chapters:
            self.delete_book(chapter.id)
            logger.info("Deleted chapter '%s'", chapter.id)

        logger.info(
            "Deleted %d chapters for basename '%s'",
            len(chapters),
            basename,
        )
        return len(chapters)


class MediaRegistry(BaseRegistry[Media]):
    """Manages the media registry (media.json).

    Specialized registry for media sources (video, podcast, blog) with all
    Media model fields. Stores media in ~/.config/paper-index-tool/media.json.

    This class extends BaseRegistry with Media-specific configuration:
        - model_class: Media
        - entity_name: "media"
        - registry_path: ~/.config/paper-index-tool/media.json

    Inherited Methods:
        list_entries, add_entry, update_entry, delete_entry, get_entry,
        entry_exists, get_all_searchable_content, export_all, import_all, count

    Convenience Aliases:
        list_media: Alias for list_entries.
        add_media: Alias for add_entry.
        update_media: Alias for update_entry.
        delete_media: Alias for delete_entry.
        get_media: Alias for get_entry.
        media_exists: Alias for entry_exists.

    Example:
        >>> registry = MediaRegistry()
        >>> media = registry.list_media()
        >>> registry.add_media(new_media)
    """

    @property
    def model_class(self) -> type[Media]:
        """Get the Media model class.

        Returns:
            The Media class for validation.
        """
        return Media

    @property
    def entity_name(self) -> str:
        """Get the entity name for media.

        Returns:
            The string "media" for use in messages.
        """
        return "media"

    @property
    def registry_path(self) -> Path:
        """Get the path to media.json.

        Returns:
            Path to ~/.config/paper-index-tool/media.json
        """
        return get_media_path()

    # =========================================================================
    # Convenience Aliases (API Consistency)
    # =========================================================================

    def list_media(self) -> list[Media]:
        """List all media sorted by ID.

        Alias for list_entries() for improved readability
        in media-specific code.

        Returns:
            List of Media objects sorted alphabetically by ID.
        """
        return self.list_entries()

    def add_media(self, media: Media) -> None:
        """Add a new media entry to the registry.

        Alias for add_entry() for API consistency.

        Args:
            media: Media to add.

        Raises:
            EntryExistsError: If media ID already exists.
        """
        self.add_entry(media)

    def update_media(self, media_id: str, updates: dict[str, object]) -> Media:
        """Update an existing media entry.

        Alias for update_entry() for API consistency.

        Args:
            media_id: ID of media to update.
            updates: Dictionary of field updates.

        Returns:
            Updated Media object.

        Raises:
            EntryNotFoundError: If media not found.
        """
        return self.update_entry(media_id, updates)

    def delete_media(self, media_id: str) -> None:
        """Delete a media entry from the registry.

        Alias for delete_entry() for API consistency.

        Args:
            media_id: ID of media to delete.

        Raises:
            EntryNotFoundError: If media not found.
        """
        self.delete_entry(media_id)

    def get_media(self, media_id: str) -> Media | None:
        """Get a media entry by ID.

        Alias for get_entry() for API consistency.

        Args:
            media_id: Media ID to look up.

        Returns:
            Media object or None if not found.
        """
        return self.get_entry(media_id)

    def media_exists(self, media_id: str) -> bool:
        """Check if a media entry exists.

        Alias for entry_exists() for API consistency.

        Args:
            media_id: Media ID to check.

        Returns:
            True if media exists, False otherwise.
        """
        return self.entry_exists(media_id)

    def rename_media(self, old_id: str, new_id: str) -> Media:
        """Rename a media entry by changing its ID.

        Alias for rename_entry() for API consistency.

        Args:
            old_id: Current media ID.
            new_id: New media ID.

        Returns:
            Renamed Media object.

        Raises:
            EntryNotFoundError: If old_id not found.
            EntryExistsError: If new_id already exists.
            ValueError: If new_id format is invalid.
        """
        return self.rename_entry(old_id, new_id)
