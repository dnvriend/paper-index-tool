"""Tests for book chapter grouping functionality.

Tests the pattern where books indexed as <basename>ch<n> (e.g., vogelgesang2023ch1)
can be queried together using just the basename (e.g., vogelgesang2023).
"""

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from paper_index_tool.models import Book
from paper_index_tool.storage.registry import BookRegistry


def create_test_book(book_id: str, **overrides: object) -> dict[str, object]:
    """Create a minimal valid Book data dict with required fields."""
    # Need at least 1000 words for full_text
    full_text_content = " ".join(
        f"This is word number {i} in the full text content for testing purposes."
        for i in range(1, 201)  # ~1200 words
    )
    base = {
        "id": book_id,
        "author": "Test Author",
        "title": "Test Book Title",
        "year": 2023,
        "pages": "1-100",
        "publisher": "Test Publisher",
        "chapter": "Chapter 1",
        "file_path_markdown": "/path/to/test.md",
        "abstract": "Test abstract content for the book.",
        "question": "What is the main question?",
        "method": "Test methodology description.",
        "gaps": "Test gaps identified.",
        "results": "Test results summary.",
        "interpretation": "Test interpretation of results.",
        "claims": "Test key claims.",
        "full_text": full_text_content,
    }
    base.update(overrides)
    return base


class TestChapterIdDetection:
    """Tests for chapter ID pattern detection."""

    def test_is_chapter_id_with_suffix(self) -> None:
        """IDs ending with ch<n> should be detected as chapter IDs."""
        assert BookRegistry.is_chapter_id("vogelgesang2023ch1") is True
        assert BookRegistry.is_chapter_id("vogelgesang2023ch11") is True
        assert BookRegistry.is_chapter_id("smith2020ch100") is True

    def test_is_chapter_id_without_suffix(self) -> None:
        """IDs without ch<n> suffix should not be detected as chapter IDs."""
        assert BookRegistry.is_chapter_id("vogelgesang2023") is False
        assert BookRegistry.is_chapter_id("smith2020") is False
        assert BookRegistry.is_chapter_id("jones2021a") is False

    def test_is_chapter_id_edge_cases(self) -> None:
        """Edge cases for chapter ID detection."""
        # 'ch' without number should not match
        assert BookRegistry.is_chapter_id("vogelgesang2023ch") is False
        # 'chapter' should not match
        assert BookRegistry.is_chapter_id("vogelgesang2023chapter1") is False


class TestBasenameExtraction:
    """Tests for extracting basename from chapter IDs."""

    def test_get_basename_from_chapter_id(self) -> None:
        """Should extract basename by removing ch<n> suffix."""
        assert BookRegistry.get_basename("vogelgesang2023ch1") == "vogelgesang2023"
        assert BookRegistry.get_basename("vogelgesang2023ch11") == "vogelgesang2023"
        assert BookRegistry.get_basename("smith2020ch5") == "smith2020"

    def test_get_basename_from_non_chapter_id(self) -> None:
        """Non-chapter IDs should return unchanged."""
        assert BookRegistry.get_basename("vogelgesang2023") == "vogelgesang2023"
        assert BookRegistry.get_basename("smith2020a") == "smith2020a"


class TestFindChapters:
    """Tests for finding chapters by basename."""

    @pytest.fixture
    def registry_with_chapters(self, tmp_path: Path) -> Generator[BookRegistry]:
        """Create a registry with test chapter data."""
        books_data = {
            "testbook2023ch1": create_test_book(
                "testbook2023ch1", chapter="Chapter 1", abstract="Abstract for chapter 1"
            ),
            "testbook2023ch2": create_test_book(
                "testbook2023ch2", chapter="Chapter 2", abstract="Abstract for chapter 2"
            ),
            "testbook2023ch10": create_test_book(
                "testbook2023ch10", chapter="Chapter 10", abstract="Abstract for chapter 10"
            ),
            "standalone2020": create_test_book(
                "standalone2020",
                year=2020,
                title="Complete Standalone Book",
                abstract="Full book abstract",
            ),
        }

        books_path = tmp_path / "books.json"
        books_path.write_text(json.dumps(books_data))

        with patch("paper_index_tool.storage.registry.get_books_path", return_value=books_path):
            yield BookRegistry()

    def test_find_chapters_returns_sorted_by_number(
        self, registry_with_chapters: BookRegistry
    ) -> None:
        """Chapters should be returned sorted by chapter number."""
        chapters = registry_with_chapters.find_chapters("testbook2023")

        assert len(chapters) == 3
        assert chapters[0].id == "testbook2023ch1"
        assert chapters[1].id == "testbook2023ch2"
        assert chapters[2].id == "testbook2023ch10"

    def test_find_chapters_returns_empty_for_no_match(
        self, registry_with_chapters: BookRegistry
    ) -> None:
        """Should return empty list when no chapters found."""
        chapters = registry_with_chapters.find_chapters("nonexistent2023")
        assert chapters == []

    def test_find_chapters_does_not_match_non_chapter_books(
        self, registry_with_chapters: BookRegistry
    ) -> None:
        """Basename without chapters should not find any matches."""
        chapters = registry_with_chapters.find_chapters("standalone2020")
        assert chapters == []


class TestGetBookOrChapters:
    """Tests for the combined get_book_or_chapters method."""

    @pytest.fixture
    def registry_with_mixed_books(self, tmp_path: Path) -> Generator[BookRegistry]:
        """Create a registry with both chapters and standalone books."""
        books_data = {
            "testbook2023ch1": create_test_book("testbook2023ch1", chapter="Chapter 1"),
            "testbook2023ch2": create_test_book("testbook2023ch2", chapter="Chapter 2"),
            "standalone2020": create_test_book(
                "standalone2020", year=2020, title="Complete Standalone Book"
            ),
        }

        books_path = tmp_path / "books.json"
        books_path.write_text(json.dumps(books_data))

        with patch("paper_index_tool.storage.registry.get_books_path", return_value=books_path):
            yield BookRegistry()

    def test_exact_match_returns_single_book(self, registry_with_mixed_books: BookRegistry) -> None:
        """Exact ID should return single Book."""
        result = registry_with_mixed_books.get_book_or_chapters("standalone2020")

        assert isinstance(result, Book)
        assert result.id == "standalone2020"

    def test_exact_chapter_id_returns_single_book(
        self, registry_with_mixed_books: BookRegistry
    ) -> None:
        """Exact chapter ID should return single Book."""
        result = registry_with_mixed_books.get_book_or_chapters("testbook2023ch1")

        assert isinstance(result, Book)
        assert result.id == "testbook2023ch1"

    def test_basename_returns_list_of_chapters(
        self, registry_with_mixed_books: BookRegistry
    ) -> None:
        """Basename should return list of chapters."""
        result = registry_with_mixed_books.get_book_or_chapters("testbook2023")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(b, Book) for b in result)

    def test_nonexistent_returns_none(self, registry_with_mixed_books: BookRegistry) -> None:
        """Non-existent ID should return None."""
        result = registry_with_mixed_books.get_book_or_chapters("nonexistent2023")
        assert result is None


class TestDeleteChapters:
    """Tests for deleting chapters by basename."""

    @pytest.fixture
    def registry_with_chapters(self, tmp_path: Path) -> Generator[BookRegistry]:
        """Create a registry with chapters that can be deleted."""
        books_data = {
            "testbook2023ch1": create_test_book("testbook2023ch1", chapter="Chapter 1"),
            "testbook2023ch2": create_test_book("testbook2023ch2", chapter="Chapter 2"),
            "standalone2020": create_test_book(
                "standalone2020", year=2020, title="Complete Standalone Book"
            ),
        }

        books_path = tmp_path / "books.json"
        books_path.write_text(json.dumps(books_data))

        with patch("paper_index_tool.storage.registry.get_books_path", return_value=books_path):
            yield BookRegistry()

    def test_delete_chapters_removes_all_matching(
        self, registry_with_chapters: BookRegistry
    ) -> None:
        """Should delete all chapters matching basename."""
        count = registry_with_chapters.delete_chapters("testbook2023")

        assert count == 2
        assert registry_with_chapters.get_book("testbook2023ch1") is None
        assert registry_with_chapters.get_book("testbook2023ch2") is None
        # Other books should remain
        assert registry_with_chapters.get_book("standalone2020") is not None

    def test_delete_chapters_raises_for_no_match(
        self, registry_with_chapters: BookRegistry
    ) -> None:
        """Should raise EntryNotFoundError when no chapters found."""
        from paper_index_tool.storage.registry import EntryNotFoundError

        with pytest.raises(EntryNotFoundError):
            registry_with_chapters.delete_chapters("nonexistent2023")
