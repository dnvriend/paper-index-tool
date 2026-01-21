"""Text chunking for vector search.

This module provides text chunking functionality that splits documents
into smaller pieces suitable for embedding, while preserving metadata
like page numbers and section headers.

Classes:
    Chunk: A text chunk with metadata.
    TextChunker: Splits text into chunks with overlap.

Chunking Strategy:
    - Target size: ~300 words per chunk
    - Overlap: 50 words between chunks
    - Page detection via [PAGE:N] markers
    - Section detection via markdown headers (## Header)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from paper_index_tool.logging_config import get_logger

logger = get_logger(__name__)

# Chunking parameters
DEFAULT_CHUNK_SIZE = 300  # words
DEFAULT_OVERLAP = 50  # words
MIN_CHUNK_SIZE = 100  # words


@dataclass
class Chunk:
    """A text chunk with metadata for vector search.

    Represents a portion of a document with tracking for its source
    location (page numbers, section, line numbers).

    Attributes:
        entry_id: ID of the source entry (paper/book/media).
        entry_type: Type of entry ("paper", "book", "media").
        chunk_index: Index of this chunk within the entry (0-based).
        text: The chunk text content.
        page_start: Starting page number (if detected).
        page_end: Ending page number (if detected).
        section: Section header (if detected, e.g., "Method").
        line_start: Starting line number in source (1-based).
        line_end: Ending line number in source (1-based).

    Example:
        >>> chunk = Chunk(
        ...     entry_id="ashford2012",
        ...     entry_type="paper",
        ...     chunk_index=0,
        ...     text="Leadership development...",
        ...     page_start=1,
        ...     page_end=2,
        ...     section="Abstract",
        ... )
    """

    entry_id: str
    entry_type: str
    chunk_index: int
    text: str
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    line_start: int = 1
    line_end: int = 1
    embedding: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert chunk to dictionary for JSON serialization.

        Returns:
            Dictionary with all chunk attributes except embedding.
        """
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "section": self.section,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        """Create chunk from dictionary.

        Args:
            data: Dictionary with chunk attributes.

        Returns:
            Chunk instance.
        """
        return cls(
            entry_id=data["entry_id"],
            entry_type=data["entry_type"],
            chunk_index=data["chunk_index"],
            text=data["text"],
            page_start=data.get("page_start"),
            page_end=data.get("page_end"),
            section=data.get("section"),
            line_start=data.get("line_start", 1),
            line_end=data.get("line_end", 1),
        )


class TextChunker:
    """Text chunker with page and section tracking.

    Splits documents into overlapping chunks suitable for embedding,
    while preserving metadata about page numbers and sections.

    Attributes:
        chunk_size: Target words per chunk.
        overlap: Words to overlap between chunks.
        min_chunk_size: Minimum words for a valid chunk.

    Example:
        >>> chunker = TextChunker(chunk_size=300, overlap=50)
        >>> chunks = chunker.chunk_text(
        ...     text="Long document text...",
        ...     entry_id="ashford2012",
        ...     entry_type="paper"
        ... )
    """

    # Regex patterns
    PAGE_PATTERN = re.compile(r"\[PAGE:(\d+)\]")
    SECTION_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
        min_chunk_size: int = MIN_CHUNK_SIZE,
    ) -> None:
        """Initialize chunker with parameters.

        Args:
            chunk_size: Target words per chunk (default 300).
            overlap: Words to overlap between chunks (default 50).
            min_chunk_size: Minimum words for a valid chunk (default 100).
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(
        self,
        text: str,
        entry_id: str,
        entry_type: str,
    ) -> list[Chunk]:
        """Split text into chunks with metadata.

        Splits the text into overlapping chunks while tracking:
        - Page numbers from [PAGE:N] markers
        - Section headers from ## markdown headers
        - Line numbers for fragment extraction

        Args:
            text: Full text content to chunk.
            entry_id: ID of the source entry.
            entry_type: Type of entry ("paper", "book", "media").

        Returns:
            List of Chunk objects with metadata.

        Example:
            >>> chunks = chunker.chunk_text(
            ...     "[PAGE:1]\\n## Abstract\\nThis paper...",
            ...     "ashford2012",
            ...     "paper"
            ... )
        """
        if not text or not text.strip():
            return []

        # Parse text into annotated lines
        lines = text.splitlines()
        annotated_lines = self._annotate_lines(lines)

        # Split into chunks
        chunks = self._create_chunks(annotated_lines, entry_id, entry_type)

        logger.debug(
            "Created %d chunks for %s (avg %d words)",
            len(chunks),
            entry_id,
            sum(len(c.text.split()) for c in chunks) // max(len(chunks), 1),
        )

        return chunks

    def _annotate_lines(self, lines: list[str]) -> list[dict[str, Any]]:
        """Annotate lines with page and section info.

        Args:
            lines: List of text lines.

        Returns:
            List of dicts with line text and metadata.
        """
        annotated = []
        current_page: int | None = None
        current_section: str | None = None

        for line_num, line in enumerate(lines, start=1):
            # Check for page marker
            page_match = self.PAGE_PATTERN.search(line)
            if page_match:
                current_page = int(page_match.group(1))
                # Remove page marker from text
                line = self.PAGE_PATTERN.sub("", line).strip()

            # Check for section header
            section_match = self.SECTION_PATTERN.match(line)
            if section_match:
                current_section = section_match.group(1).strip()

            annotated.append(
                {
                    "line_num": line_num,
                    "text": line,
                    "page": current_page,
                    "section": current_section,
                }
            )

        return annotated

    def _create_chunks(
        self,
        annotated_lines: list[dict[str, Any]],
        entry_id: str,
        entry_type: str,
    ) -> list[Chunk]:
        """Create chunks from annotated lines.

        Uses a sliding window approach with overlap.

        Args:
            annotated_lines: Lines with metadata.
            entry_id: Source entry ID.
            entry_type: Source entry type.

        Returns:
            List of Chunk objects.
        """
        chunks: list[Chunk] = []

        # Collect all words with their metadata
        words_with_meta: list[dict[str, Any]] = []
        for line_data in annotated_lines:
            line_text = line_data["text"]
            if not line_text.strip():
                continue
            words = line_text.split()
            for word in words:
                words_with_meta.append(
                    {
                        "word": word,
                        "line_num": line_data["line_num"],
                        "page": line_data["page"],
                        "section": line_data["section"],
                    }
                )

        if not words_with_meta:
            return []

        # Create chunks using sliding window
        chunk_index = 0
        start_idx = 0

        while start_idx < len(words_with_meta):
            # Determine chunk end
            end_idx = min(start_idx + self.chunk_size, len(words_with_meta))

            # Extract chunk words and metadata
            chunk_words = words_with_meta[start_idx:end_idx]

            if len(chunk_words) < self.min_chunk_size and chunks:
                # Too small and not first chunk - merge with previous or skip
                break

            # Build chunk text
            text = " ".join(w["word"] for w in chunk_words)

            # Get metadata from chunk words
            pages = [w["page"] for w in chunk_words if w["page"] is not None]
            sections = [w["section"] for w in chunk_words if w["section"] is not None]
            line_nums = [w["line_num"] for w in chunk_words]

            chunk = Chunk(
                entry_id=entry_id,
                entry_type=entry_type,
                chunk_index=chunk_index,
                text=text,
                page_start=min(pages) if pages else None,
                page_end=max(pages) if pages else None,
                section=sections[0] if sections else None,
                line_start=min(line_nums),
                line_end=max(line_nums),
            )
            chunks.append(chunk)

            # Move window with overlap
            start_idx += self.chunk_size - self.overlap
            chunk_index += 1

            # Safety check for infinite loop
            if start_idx <= 0:
                break

        return chunks
