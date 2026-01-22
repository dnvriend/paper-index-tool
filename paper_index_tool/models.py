"""Data models for paper-index-tool.

This module provides Pydantic v2 models for academic paper and book metadata
with comprehensive validation. Models follow SOLID principles with reusable
validators and agent-friendly error messages.

Models:
    Quote: A verbatim quote from a paper/book with page reference.
    Paper: Academic paper with bibtex metadata and content fields.
    Book: Book/book chapter with bibtex metadata and content fields.
    Media: Video, podcast, or blog source with bibtex metadata and content fields.

Enums:
    MediaType: Type of media source (video, podcast, blog).

Field Lists:
    PAPER_BIBTEX_FIELDS: List of bibtex field names for Paper model.
    PAPER_CONTENT_FIELDS: List of content field names for Paper model.
    BOOK_BIBTEX_FIELDS: List of bibtex field names for Book model.
    BOOK_CONTENT_FIELDS: List of content field names for Book model.
    MEDIA_BIBTEX_FIELDS: List of bibtex field names for Media model.
    MEDIA_CONTENT_FIELDS: List of content field names for Media model.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# =============================================================================
# Enums
# =============================================================================


class MediaType(str, Enum):
    """Type of media source.

    Values:
        VIDEO: YouTube, Vimeo, educational videos (exports as @misc).
        PODCAST: Audio content with transcripts (exports as @misc).
        BLOG: Website articles, blog posts (exports as @online).
    """

    VIDEO = "video"
    PODCAST = "podcast"
    BLOG = "blog"


# =============================================================================
# Reusable Validator Functions (SOLID - Single Responsibility)
# =============================================================================


def validate_id_format(value: str, field_name: str = "id") -> str:
    """Validate ID format matches <surname><year>[suffix] pattern.

    Args:
        value: The ID string to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated ID string (lowercase).

    Raises:
        ValueError: If ID format is invalid with agent-friendly guidance.

    Example:
        >>> validate_id_format("ashford2012")
        'ashford2012'
        >>> validate_id_format("Adams2012a")
        'adams2012a'
        >>> validate_id_format("vogelgesang2023ch1")
        'vogelgesang2023ch1'
    """
    # Allow <surname><year> optionally followed by a single letter OR 'ch' + digits
    pattern = r"^[a-z]+\d{4}([a-z]|ch\d+)?$"
    value_lower = value.lower()
    if not re.match(pattern, value_lower):
        raise ValueError(
            f"Invalid {field_name} format: '{value}'. "
            f"Expected format: <surname><year>[suffix], "
            f"e.g., 'ashford2012', 'adams2012a', or 'vogelgesang2023ch1'. "
            f"Rules: lowercase letters followed by 4-digit year, "
            f"optional suffix (letter or ch + number)."
        )
    return value_lower


def validate_min_length(value: str, min_len: int, field_name: str) -> str:
    """Validate string has minimum length.

    Args:
        value: The string to validate.
        min_len: Minimum required length.
        field_name: Name of the field for error messages.

    Returns:
        The validated string.

    Raises:
        ValueError: If string is too short with agent-friendly guidance.
    """
    if len(value.strip()) < min_len:
        raise ValueError(
            f"Field '{field_name}' is too short: {len(value.strip())} characters. "
            f"Minimum required: {min_len} characters. "
            f"Current value: '{value[:50]}{'...' if len(value) > 50 else ''}'. "
            f"Please provide a more complete value."
        )
    return value


def validate_year(value: int, field_name: str = "year") -> int:
    """Validate year is a valid 4-digit year.

    Args:
        value: The year to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated year.

    Raises:
        ValueError: If year is invalid with agent-friendly guidance.
    """
    current_year = datetime.now().year
    if value < 1900 or value > current_year + 1:
        raise ValueError(
            f"Invalid {field_name}: {value}. "
            f"Year must be between 1900 and {current_year + 1}. "
            f"Please provide a valid 4-digit publication year."
        )
    return value


def validate_url(value: str | None, field_name: str = "url") -> str | None:
    """Validate URL format (http/https).

    Args:
        value: The URL to validate (can be None).
        field_name: Name of the field for error messages.

    Returns:
        The validated URL or None.

    Raises:
        ValueError: If URL format is invalid with agent-friendly guidance.
    """
    if value is None:
        return None
    pattern = r"^https?://[^\s]+"
    if not re.match(pattern, value):
        raise ValueError(
            f"Invalid {field_name} format: '{value}'. "
            f"URL must start with 'http://' or 'https://'. "
            f"Example: 'https://doi.org/10.1234/example'"
        )
    return value


def validate_file_path(value: str, field_name: str) -> str:
    """Validate file path format.

    Args:
        value: The file path to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated file path.

    Raises:
        ValueError: If file path format is invalid with agent-friendly guidance.
    """
    # Allow absolute paths (Unix/Mac or Windows) or relative paths
    pattern = r"^(/|~|[A-Za-z]:\\|\.\.?/)"
    if not re.match(pattern, value):
        raise ValueError(
            f"Invalid {field_name} format: '{value}'. "
            f"Path must be absolute (starting with /, ~, or drive letter like C:\\) "
            f"or relative (starting with ./ or ../). "
            f"Example: '/Users/dennis/papers/ashford2012.pdf' or './papers/ashford2012.pdf'"
        )
    return value


def validate_rating(value: int, field_name: str = "rating") -> int:
    """Validate rating is between 1-5.

    Args:
        value: The rating to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated rating.

    Raises:
        ValueError: If rating is out of range with agent-friendly guidance.
    """
    if value < 1 or value > 5:
        raise ValueError(
            f"Invalid {field_name}: {value}. "
            f"Rating must be between 1 (lowest) and 5 (highest). "
            f"Scale: 1=Poor, 2=Fair, 3=Good, 4=Very Good, 5=Excellent."
        )
    return value


def validate_date_format(value: str, field_name: str = "date") -> str:
    """Validate date is in YYYY-MM-DD format.

    Args:
        value: The date string to validate.
        field_name: Name of the field for error messages.

    Returns:
        The validated date string.

    Raises:
        ValueError: If date format is invalid with agent-friendly guidance.
    """
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(pattern, value):
        raise ValueError(
            f"Invalid {field_name} format: '{value}'. "
            f"Date must be in YYYY-MM-DD format, e.g., '2025-01-21'. "
            f"Please provide a valid date."
        )
    # Also validate it's a real date
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"Invalid {field_name}: '{value}' is not a valid date. "
            f"Please provide a valid date in YYYY-MM-DD format."
        )
    return value


def validate_required_url(value: str, field_name: str = "url") -> str:
    """Validate URL format (http/https) - required field.

    Args:
        value: The URL to validate (required).
        field_name: Name of the field for error messages.

    Returns:
        The validated URL.

    Raises:
        ValueError: If URL format is invalid with agent-friendly guidance.
    """
    pattern = r"^https?://[^\s]+"
    if not re.match(pattern, value):
        raise ValueError(
            f"Invalid {field_name} format: '{value}'. "
            f"URL must start with 'http://' or 'https://'. "
            f"Example: 'https://youtube.com/watch?v=abc123'"
        )
    return value


def validate_max_words(value: str, max_words: int, field_name: str) -> str:
    """Validate string does not exceed maximum word count.

    Args:
        value: The string to validate.
        max_words: Maximum allowed word count.
        field_name: Name of the field for error messages.

    Returns:
        The validated string.

    Raises:
        ValueError: If word count exceeds maximum with agent-friendly guidance.
    """
    word_count = len(value.split())
    if word_count > max_words:
        raise ValueError(
            f"Field '{field_name}' exceeds maximum word count: {word_count} words. "
            f"Maximum allowed: {max_words} words. "
            f"Please condense the content to fit within the limit."
        )
    return value


def validate_min_words(value: str, min_words: int, field_name: str) -> str:
    """Validate string has minimum word count.

    Args:
        value: The string to validate.
        min_words: Minimum required word count.
        field_name: Name of the field for error messages.

    Returns:
        The validated string.

    Raises:
        ValueError: If word count is below minimum with agent-friendly guidance.
    """
    word_count = len(value.split())
    if word_count < min_words:
        raise ValueError(
            f"Field '{field_name}' has insufficient content: {word_count} words. "
            f"Minimum required: {min_words} words. "
            f"Please provide more comprehensive content."
        )
    return value


def validate_quotes_min_count(quotes: list[Quote], min_count: int = 10) -> list[Quote]:
    """Validate quotes list has minimum number of entries.

    Args:
        quotes: List of Quote objects to validate.
        min_count: Minimum required number of quotes.

    Returns:
        The validated quotes list.

    Raises:
        ValueError: If quote count is below minimum with agent-friendly guidance.
    """
    if len(quotes) < min_count:
        raise ValueError(
            f"Insufficient quotes: {len(quotes)} provided. "
            f"Minimum required: {min_count} quotes with page references. "
            f"Please extract at least {min_count} verbatim quotes from the source "
            f"to support claims and enable citation verification."
        )
    return quotes


# =============================================================================
# Quote Model
# =============================================================================


class Quote(BaseModel):
    """A verbatim quote from a paper/book/media with page or timestamp reference.

    Used for citation verification and grounding claims in source material.
    Each quote must include the exact text and either a page number (for papers/books)
    or a timestamp (for video/podcast media).

    Attributes:
        text: The verbatim quote text (must be at least 10 characters).
        page: Page number where quote appears (for papers/books).
        timestamp: Timestamp for video/podcast (HH:MM:SS or MM:SS format).

    Example:
        >>> quote = Quote(text="Leadership is a process...", page=42)
        >>> media_quote = Quote(text="The key insight here is...", timestamp="05:30")
    """

    text: str = Field(min_length=10, description="The verbatim quote text (minimum 10 characters)")
    page: int | None = Field(
        default=None, gt=0, description="Page number where quote appears (for papers/books)"
    )
    timestamp: str | None = Field(
        default=None, description="Timestamp for video/podcast (HH:MM:SS or MM:SS)"
    )

    @field_validator("text")
    @classmethod
    def validate_text_not_empty(cls, v: str) -> str:
        """Ensure quote text is meaningful, not just whitespace."""
        if not v.strip():
            raise ValueError(
                "Quote text cannot be empty or whitespace only. "
                "Please provide the exact verbatim text from the source."
            )
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_format(cls, v: str | None) -> str | None:
        """Validate timestamp format (HH:MM:SS or MM:SS)."""
        if v is None:
            return None
        pattern = r"^(\d{1,2}:)?\d{1,2}:\d{2}$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid timestamp format: '{v}'. "
                f"Timestamp must be in HH:MM:SS or MM:SS format, e.g., '05:30' or '01:23:45'."
            )
        return v


# =============================================================================
# Paper Model
# =============================================================================


class Paper(BaseModel):
    """Academic paper entry with bibtex metadata and searchable content.

    This model represents a peer-reviewed academic paper with comprehensive
    metadata for citation management and content fields for search/analysis.
    All fields are mandatory to ensure agent-friendly completeness.

    Bibtex Fields:
        id, author, title, year, journal, volume, number, issue, pages,
        publisher, doi, url (optional), file_path_pdf, file_path_markdown,
        keywords, rating, peer_reviewed

    Content Fields:
        abstract, question, method, gaps, results, interpretation, claims,
        quotes, full_text

    Methods:
        get_searchable_text(): Combine all content for BM25 indexing.
        to_bibtex(): Export as bibtex @article entry.

    Example:
        >>> paper = Paper(
        ...     id="ashford2012",
        ...     author="Ashford, S. J., & DeRue, D. S.",
        ...     title="Developing as a leader",
        ...     year=2012,
        ...     journal="Organizational Dynamics",
        ...     ...
        ... )
    """

    # =========================================================================
    # Identity
    # =========================================================================
    id: str = Field(
        description="Unique paper ID in format <surname><year>[a-z], e.g., 'ashford2012'"
    )

    # =========================================================================
    # Bibtex Fields (Extended)
    # =========================================================================
    author: str = Field(
        min_length=2, description="Author(s) in 'Last, First' format, multiple separated by 'and'"
    )
    title: str = Field(min_length=5, description="Full paper title")
    year: int = Field(description="4-digit publication year (1900-present)")
    journal: str = Field(min_length=5, description="Journal name where paper was published")
    volume: str = Field(default="", description="Journal volume number")
    number: str = Field(default="", description="Journal number within volume")
    issue: str = Field(default="", description="Journal issue number")
    pages: str = Field(default="", description="Page range, e.g., '219-235'")
    publisher: str = Field(default="", description="Publisher name")
    doi: str = Field(default="", description="Digital Object Identifier")
    url: str | None = Field(
        default=None, description="URL to paper (must start with http:// or https://)"
    )
    file_path_pdf: str = Field(default="", description="Absolute path to PDF file")
    file_path_markdown: str = Field(description="Absolute path to markdown file")
    keywords: str = Field(default="", description="Comma-separated keywords for categorization")
    rating: int = Field(
        default=3, ge=1, le=5, description="Quality rating 1-5 (1=Poor, 5=Excellent)"
    )
    peer_reviewed: bool = Field(default=True, description="Whether the paper is peer-reviewed")

    # =========================================================================
    # Content Fields (Searchable)
    # =========================================================================
    abstract: str = Field(description="Paper abstract (max 1000 words)")
    question: str = Field(description="Research question the paper addresses (max 1000 words)")
    method: str = Field(description="Research methodology used (max 1000 words)")
    gaps: str = Field(description="Identified gaps or limitations (max 1000 words)")
    results: str = Field(description="Key results and findings (max 1000 words)")
    interpretation: str = Field(description="Interpretation of results (max 1000 words)")
    claims: str = Field(description="Key verifiable claims (max 1000 words)")
    quotes: list[Quote] = Field(
        default_factory=list, description="Verbatim quotes with page refs (min 10 entries)"
    )
    full_text: str = Field(description="Full paper content in markdown (min 1000 words)")

    # =========================================================================
    # Metadata
    # =========================================================================
    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when entry was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when entry was last updated"
    )

    # =========================================================================
    # AI Generation Tracking
    # =========================================================================
    ai_generated: bool = Field(default=False, description="Whether content was AI-generated")
    ai_provider: str | None = Field(
        default=None, description="AI provider: anthropic, openai, google, meta, mistral, other"
    )
    ai_model: str | None = Field(
        default=None, description="AI model identifier, e.g., claude-sonnet-4-20250514"
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate paper ID format."""
        return validate_id_format(v, "id")

    @field_validator("author")
    @classmethod
    def validate_author(cls, v: str) -> str:
        """Validate author has minimum length."""
        return validate_min_length(v, 2, "author")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title has minimum length."""
        return validate_min_length(v, 5, "title")

    @field_validator("year")
    @classmethod
    def validate_year_field(cls, v: int) -> int:
        """Validate year is a valid 4-digit year."""
        return validate_year(v, "year")

    @field_validator("journal")
    @classmethod
    def validate_journal(cls, v: str) -> str:
        """Validate journal has minimum length."""
        return validate_min_length(v, 5, "journal")

    @field_validator("volume", "number", "issue")
    @classmethod
    def validate_volume_number_issue(cls, v: str) -> str:
        """Validate volume/number/issue - allow empty strings as default."""
        # Always allow empty strings
        return v

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, v: str) -> str:
        """Validate pages - allow empty strings as default."""
        if v == "":
            return v
        return validate_min_length(v, 1, "pages")

    @field_validator("publisher")
    @classmethod
    def validate_publisher(cls, v: str) -> str:
        """Validate publisher - allow empty strings as default."""
        # Always allow empty strings
        return v

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, v: str) -> str:
        """Validate DOI - allow empty strings as default."""
        if v == "":
            return v
        return validate_min_length(v, 2, "doi")

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str | None) -> str | None:
        """Validate URL format if provided - allow empty strings and None."""
        if v == "" or v is None:
            return None
        return validate_url(v, "url")

    @field_validator("file_path_pdf")
    @classmethod
    def validate_file_path_pdf(cls, v: str) -> str:
        """Validate PDF file path format - allow empty strings as default."""
        # Always allow empty strings
        if not v or v == "":
            return ""
        return validate_file_path(v, "file_path_pdf")

    @field_validator("file_path_markdown")
    @classmethod
    def validate_file_path_markdown(cls, v: str) -> str:
        """Validate markdown file path format."""
        return validate_file_path(v, "file_path_markdown")

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: str) -> str:
        """Validate keywords - allow empty strings as default."""
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating_field(cls, v: int) -> int:
        """Validate rating is between 1-5."""
        return validate_rating(v, "rating")

    @field_validator(
        "abstract", "question", "method", "gaps", "results", "interpretation", "claims"
    )
    @classmethod
    def validate_content_max_words(cls, v: str, info: Any) -> str:
        """Validate content fields do not exceed 1000 words."""
        return validate_max_words(v, 1000, info.field_name)

    @field_validator("full_text")
    @classmethod
    def validate_full_text(cls, v: str) -> str:
        """Validate full_text has minimum 1000 words."""
        return validate_min_words(v, 1000, "full_text")

    @field_validator("quotes")
    @classmethod
    def validate_quotes(cls, v: list[Quote]) -> list[Quote]:
        """Validate quotes list - allow empty list for flexibility."""
        return v

    @model_validator(mode="before")
    @classmethod
    def set_updated_at(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Update the updated_at timestamp on any modification."""
        values["updated_at"] = datetime.now()
        return values

    @model_validator(mode="after")
    def validate_ai_provider_value(self) -> Paper:
        """Validate ai_provider is one of allowed values when ai_generated is True."""
        valid_providers = {"anthropic", "openai", "google", "meta", "mistral", "other"}
        if self.ai_generated and self.ai_provider is not None:
            if self.ai_provider not in valid_providers:
                raise ValueError(
                    f"Invalid ai_provider: '{self.ai_provider}'. "
                    f"When ai_generated=True, ai_provider must be one of: "
                    f"{', '.join(sorted(valid_providers))}."
                )
        return self

    # =========================================================================
    # Methods
    # =========================================================================

    def get_searchable_text(self) -> str:
        """Combine all searchable content fields into one text block.

        Used for BM25 full-text indexing. Combines abstract, question, method,
        gaps, results, interpretation, claims, full_text, and quote texts.

        Returns:
            Combined text from all content fields for BM25 indexing.

        Example:
            >>> text = paper.get_searchable_text()
            >>> len(text) > 0
            True
        """
        parts = [
            self.abstract,
            self.question,
            self.method,
            self.gaps,
            self.results,
            self.interpretation,
            self.claims,
            self.full_text,
        ]
        # Add quote texts
        for quote in self.quotes:
            parts.append(quote.text)
        return "\n\n".join(parts)

    def to_bibtex(self) -> str:
        """Export paper as bibtex @article entry.

        Generates a properly formatted bibtex entry with all available
        bibtex fields. Uses @article type for journal papers.

        Returns:
            Bibtex formatted string ready for .bib file.

        Example:
            >>> bibtex = paper.to_bibtex()
            >>> bibtex.startswith("@article{")
            True
        """
        lines = [f"@article{{{self.id},"]
        lines.append(f"  author = {{{self.author}}},")
        lines.append(f"  title = {{{self.title}}},")
        lines.append(f"  year = {{{self.year}}},")
        lines.append(f"  journal = {{{self.journal}}},")
        lines.append(f"  volume = {{{self.volume}}},")
        lines.append(f"  number = {{{self.number}}},")
        lines.append(f"  pages = {{{self.pages}}},")
        lines.append(f"  publisher = {{{self.publisher}}},")
        lines.append(f"  doi = {{{self.doi}}},")
        if self.url:
            lines.append(f"  url = {{{self.url}}},")
        lines.append(f"  file = {{{self.file_path_pdf}}},")
        lines.append(f"  keywords = {{{self.keywords}}},")
        if self.ai_generated:
            provider = self.ai_provider or "unknown"
            model = self.ai_model or "unknown"
            lines.append(f"  note = {{AI-generated using {provider} {model}}},")
        lines.append(f"  abstract = {{{self.abstract}}}")
        lines.append("}")
        return "\n".join(lines)


# =============================================================================
# Book Model
# =============================================================================


class Book(BaseModel):
    """Book or book chapter entry with bibtex metadata and searchable content.

    This model represents a book or book chapter with comprehensive metadata
    for citation management and content fields for search/analysis.
    All fields are mandatory to ensure agent-friendly completeness.

    Bibtex Fields:
        id, author, title, year, pages, publisher, url (optional),
        isbn (optional), chapter, file_path_pdf, file_path_markdown, keywords

    Content Fields:
        abstract, question, method, gaps, results, interpretation, claims,
        quotes, full_text

    Methods:
        get_searchable_text(): Combine all content for BM25 indexing.
        to_bibtex(): Export as bibtex @book entry.

    Example:
        >>> book = Book(
        ...     id="vogelgesang2023",
        ...     author="Vogelgesang Lester, Gretchen",
        ...     title="Applied Organizational Behavior",
        ...     year=2023,
        ...     ...
        ... )
    """

    # =========================================================================
    # Identity
    # =========================================================================
    id: str = Field(
        description="Unique book ID in format <surname><year>[a-z], e.g., 'vogelgesang2023'"
    )

    # =========================================================================
    # Bibtex Fields
    # =========================================================================
    author: str = Field(
        min_length=2, description="Author(s) in 'Last, First' format, multiple separated by 'and'"
    )
    title: str = Field(min_length=5, description="Full book title")
    year: int = Field(description="4-digit publication year (1900-present)")
    pages: str = Field(default="", description="Page range or total pages, e.g., '1-50' or '350'")
    publisher: str = Field(min_length=2, description="Publisher name")
    url: str | None = Field(
        default=None, description="URL to book (must start with http:// or https://)"
    )
    isbn: str | None = Field(default=None, description="ISBN number")
    chapter: str = Field(min_length=2, description="Chapter title or number")
    file_path_pdf: str = Field(default="", description="Absolute path to PDF file")
    file_path_markdown: str = Field(description="Absolute path to markdown file")
    keywords: str = Field(default="", description="Comma-separated keywords for categorization")

    # =========================================================================
    # Content Fields (Searchable) - Same as Paper
    # =========================================================================
    abstract: str = Field(description="Book/chapter abstract (max 1000 words)")
    question: str = Field(description="Main question or thesis addressed (max 1000 words)")
    method: str = Field(description="Methodology or approach used (max 1000 words)")
    gaps: str = Field(description="Identified gaps or limitations (max 1000 words)")
    results: str = Field(description="Key results and findings (max 1000 words)")
    interpretation: str = Field(description="Interpretation of results (max 1000 words)")
    claims: str = Field(description="Key verifiable claims (max 1000 words)")
    quotes: list[Quote] = Field(
        default_factory=list, description="Verbatim quotes with page refs (min 10 entries)"
    )
    full_text: str = Field(description="Full book/chapter content in markdown (min 1000 words)")

    # =========================================================================
    # Metadata
    # =========================================================================
    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when entry was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when entry was last updated"
    )

    # =========================================================================
    # AI Generation Tracking
    # =========================================================================
    ai_generated: bool = Field(default=False, description="Whether content was AI-generated")
    ai_provider: str | None = Field(
        default=None, description="AI provider: anthropic, openai, google, meta, mistral, other"
    )
    ai_model: str | None = Field(
        default=None, description="AI model identifier, e.g., claude-sonnet-4-20250514"
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate book ID format."""
        return validate_id_format(v, "id")

    @field_validator("author")
    @classmethod
    def validate_author(cls, v: str) -> str:
        """Validate author has minimum length."""
        return validate_min_length(v, 2, "author")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title has minimum length."""
        return validate_min_length(v, 5, "title")

    @field_validator("year")
    @classmethod
    def validate_year_field(cls, v: int) -> int:
        """Validate year is a valid 4-digit year."""
        return validate_year(v, "year")

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, v: str) -> str:
        """Validate pages - allow empty strings as default."""
        if v == "":
            return v
        return validate_min_length(v, 1, "pages")

    @field_validator("publisher")
    @classmethod
    def validate_publisher(cls, v: str) -> str:
        """Validate publisher - allow empty strings as default."""
        # Always allow empty strings
        return v

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str | None) -> str | None:
        """Validate URL format if provided - allow empty strings and None."""
        if v == "" or v is None:
            return None
        return validate_url(v, "url")

    @field_validator("chapter")
    @classmethod
    def validate_chapter(cls, v: str) -> str:
        """Validate chapter has minimum length."""
        return validate_min_length(v, 2, "chapter")

    @field_validator("file_path_pdf")
    @classmethod
    def validate_file_path_pdf(cls, v: str) -> str:
        """Validate PDF file path format - allow empty strings as default."""
        # Always allow empty strings
        if not v or v == "":
            return ""
        return validate_file_path(v, "file_path_pdf")

    @field_validator("file_path_markdown")
    @classmethod
    def validate_file_path_markdown(cls, v: str) -> str:
        """Validate markdown file path format."""
        return validate_file_path(v, "file_path_markdown")

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: str) -> str:
        """Validate keywords - allow empty strings as default."""
        return v

    @field_validator(
        "abstract", "question", "method", "gaps", "results", "interpretation", "claims"
    )
    @classmethod
    def validate_content_max_words(cls, v: str, info: Any) -> str:
        """Validate content fields do not exceed 1000 words."""
        return validate_max_words(v, 1000, info.field_name)

    @field_validator("full_text")
    @classmethod
    def validate_full_text(cls, v: str) -> str:
        """Validate full_text has minimum 1000 words."""
        return validate_min_words(v, 1000, "full_text")

    @field_validator("quotes")
    @classmethod
    def validate_quotes(cls, v: list[Quote]) -> list[Quote]:
        """Validate quotes list - allow empty list for flexibility."""
        return v

    @model_validator(mode="before")
    @classmethod
    def set_updated_at(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Update the updated_at timestamp on any modification."""
        values["updated_at"] = datetime.now()
        return values

    @model_validator(mode="after")
    def validate_ai_provider_value(self) -> Book:
        """Validate ai_provider is one of allowed values when ai_generated is True."""
        valid_providers = {"anthropic", "openai", "google", "meta", "mistral", "other"}
        if self.ai_generated and self.ai_provider is not None:
            if self.ai_provider not in valid_providers:
                raise ValueError(
                    f"Invalid ai_provider: '{self.ai_provider}'. "
                    f"When ai_generated=True, ai_provider must be one of: "
                    f"{', '.join(sorted(valid_providers))}."
                )
        return self

    # =========================================================================
    # Methods
    # =========================================================================

    def get_searchable_text(self) -> str:
        """Combine all searchable content fields into one text block.

        Used for BM25 full-text indexing. Combines abstract, question, method,
        gaps, results, interpretation, claims, full_text, and quote texts.

        Returns:
            Combined text from all content fields for BM25 indexing.

        Example:
            >>> text = book.get_searchable_text()
            >>> len(text) > 0
            True
        """
        parts = [
            self.abstract,
            self.question,
            self.method,
            self.gaps,
            self.results,
            self.interpretation,
            self.claims,
            self.full_text,
        ]
        # Add quote texts
        for quote in self.quotes:
            parts.append(quote.text)
        return "\n\n".join(parts)

    def to_bibtex(self) -> str:
        """Export book as bibtex @book entry.

        Generates a properly formatted bibtex entry with all available
        bibtex fields. Uses @book type.

        Returns:
            Bibtex formatted string ready for .bib file.

        Example:
            >>> bibtex = book.to_bibtex()
            >>> bibtex.startswith("@book{")
            True
        """
        lines = [f"@book{{{self.id},"]
        lines.append(f"  author = {{{self.author}}},")
        lines.append(f"  title = {{{self.title}}},")
        lines.append(f"  year = {{{self.year}}},")
        lines.append(f"  publisher = {{{self.publisher}}},")
        lines.append(f"  pages = {{{self.pages}}},")
        lines.append(f"  chapter = {{{self.chapter}}},")
        if self.isbn:
            lines.append(f"  isbn = {{{self.isbn}}},")
        if self.url:
            lines.append(f"  url = {{{self.url}}},")
        lines.append(f"  file = {{{self.file_path_pdf}}},")
        lines.append(f"  keywords = {{{self.keywords}}},")
        if self.ai_generated:
            provider = self.ai_provider or "unknown"
            model = self.ai_model or "unknown"
            lines.append(f"  note = {{AI-generated using {provider} {model}}},")
        lines.append("}")
        return "\n".join(lines)


# =============================================================================
# Media Model
# =============================================================================


class Media(BaseModel):
    """Media entry (video, podcast, blog) with bibtex metadata and searchable content.

    This model represents non-traditional academic sources like YouTube videos,
    podcasts, and blog posts with comprehensive metadata for citation management
    and content fields for search/analysis.

    Bibtex Fields:
        id, media_type, author, title, year, url (required), access_date,
        keywords, rating, platform, channel, duration, video_id, show_name,
        episode, season, host, guest, website, last_updated, file_path_markdown,
        file_path_pdf, file_path_media

    Content Fields:
        abstract, question, method, gaps, results, interpretation, claims,
        quotes, full_text

    AI Tracking Fields:
        ai_generated, ai_provider, ai_model

    Methods:
        get_searchable_text(): Combine all content for BM25 indexing.
        to_bibtex(): Export as bibtex @misc (video/podcast) or @online (blog) entry.

    Example:
        >>> media = Media(
        ...     id="ashford2017",
        ...     media_type=MediaType.PODCAST,
        ...     author="Ashford, Susan J.",
        ...     title="Why Everyone Should See Themselves as a Leader",
        ...     year=2017,
        ...     url="https://hbr.org/podcast/2017/08/...",
        ...     access_date="2025-01-21",
        ...     ...
        ... )
    """

    # =========================================================================
    # Identity
    # =========================================================================
    id: str = Field(
        description="Unique media ID in format <surname><year>[a-z], e.g., 'ashford2017'"
    )
    media_type: MediaType = Field(description="Type of media: video, podcast, or blog")

    # =========================================================================
    # Core BibTeX Fields (All Media Types)
    # =========================================================================
    author: str = Field(
        min_length=2,
        description="Creator/speaker/host name(s) in 'Last, First' format",
    )
    title: str = Field(min_length=5, description="Title of video/episode/post")
    year: int = Field(description="4-digit publication year (1900-present)")
    url: str = Field(description="Primary URL (required for media)")
    access_date: str = Field(description="Date accessed in YYYY-MM-DD format")
    keywords: str = Field(default="", description="Comma-separated keywords for categorization")
    rating: int = Field(
        default=3, ge=1, le=5, description="Quality rating 1-5 (1=Poor, 5=Excellent)"
    )

    # =========================================================================
    # Video-Specific Fields
    # =========================================================================
    platform: str = Field(default="", description="Platform name (YouTube, Vimeo, etc.)")
    channel: str = Field(default="", description="Channel/creator name")
    duration: str = Field(default="", description="Duration in HH:MM:SS or MM:SS")
    video_id: str = Field(default="", description="Platform-specific video ID")

    # =========================================================================
    # Podcast-Specific Fields
    # =========================================================================
    show_name: str = Field(default="", description="Podcast show/series name")
    episode: str = Field(default="", description="Episode number or identifier")
    season: str = Field(default="", description="Season number")
    host: str = Field(default="", description="Host name(s)")
    guest: str = Field(default="", description="Guest name(s)")

    # =========================================================================
    # Blog-Specific Fields
    # =========================================================================
    website: str = Field(default="", description="Website/publication name")
    last_updated: str | None = Field(default=None, description="Last update date in YYYY-MM-DD")

    # =========================================================================
    # File Paths
    # =========================================================================
    file_path_markdown: str = Field(description="Absolute path to transcript/content markdown")
    file_path_pdf: str = Field(default="", description="Absolute path to PDF (if available)")
    file_path_media: str = Field(default="", description="Absolute path to downloaded media file")

    # =========================================================================
    # Content Fields (Searchable) - Same as Paper/Book
    # =========================================================================
    abstract: str = Field(description="Summary (max 1000 words)")
    question: str = Field(description="Main topic/question addressed (max 1000 words)")
    method: str = Field(description="Approach/structure (max 1000 words)")
    gaps: str = Field(description="Limitations (max 1000 words)")
    results: str = Field(description="Key points/findings (max 1000 words)")
    interpretation: str = Field(description="Analysis/implications (max 1000 words)")
    claims: str = Field(description="Verifiable claims (max 1000 words)")
    quotes: list[Quote] = Field(
        default_factory=list, description="Verbatim quotes with timestamps (min 10 entries)"
    )
    full_text: str = Field(description="Full transcript/content in markdown (min 1000 words)")

    # =========================================================================
    # AI Generation Tracking
    # =========================================================================
    ai_generated: bool = Field(default=False, description="Whether content was AI-generated")
    ai_provider: str | None = Field(
        default=None, description="AI service provider (if ai_generated=True)"
    )
    ai_model: str | None = Field(
        default=None, description="Specific AI model used (if ai_generated=True)"
    )

    # =========================================================================
    # Metadata
    # =========================================================================
    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when entry was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when entry was last updated"
    )

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate media ID format."""
        return validate_id_format(v, "id")

    @field_validator("author")
    @classmethod
    def validate_author(cls, v: str) -> str:
        """Validate author has minimum length."""
        return validate_min_length(v, 2, "author")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title has minimum length."""
        return validate_min_length(v, 5, "title")

    @field_validator("year")
    @classmethod
    def validate_year_field(cls, v: int) -> int:
        """Validate year is a valid 4-digit year."""
        return validate_year(v, "year")

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        """Validate URL format - required for media."""
        return validate_required_url(v, "url")

    @field_validator("access_date")
    @classmethod
    def validate_access_date(cls, v: str) -> str:
        """Validate access_date format (YYYY-MM-DD)."""
        return validate_date_format(v, "access_date")

    @field_validator("rating")
    @classmethod
    def validate_rating_field(cls, v: int) -> int:
        """Validate rating is between 1-5."""
        return validate_rating(v, "rating")

    @field_validator("last_updated")
    @classmethod
    def validate_last_updated(cls, v: str | None) -> str | None:
        """Validate last_updated format if provided."""
        if v is None or v == "":
            return None
        return validate_date_format(v, "last_updated")

    @field_validator("file_path_markdown")
    @classmethod
    def validate_file_path_markdown(cls, v: str) -> str:
        """Validate markdown file path format."""
        return validate_file_path(v, "file_path_markdown")

    @field_validator("file_path_pdf")
    @classmethod
    def validate_file_path_pdf(cls, v: str) -> str:
        """Validate PDF file path format - allow empty strings as default."""
        if not v or v == "":
            return ""
        return validate_file_path(v, "file_path_pdf")

    @field_validator("file_path_media")
    @classmethod
    def validate_file_path_media(cls, v: str) -> str:
        """Validate media file path format - allow empty strings as default."""
        if not v or v == "":
            return ""
        return validate_file_path(v, "file_path_media")

    @field_validator(
        "abstract", "question", "method", "gaps", "results", "interpretation", "claims"
    )
    @classmethod
    def validate_content_max_words(cls, v: str, info: Any) -> str:
        """Validate content fields do not exceed 1000 words."""
        return validate_max_words(v, 1000, info.field_name)

    @field_validator("full_text")
    @classmethod
    def validate_full_text(cls, v: str) -> str:
        """Validate full_text has minimum 1000 words."""
        return validate_min_words(v, 1000, "full_text")

    @field_validator("quotes")
    @classmethod
    def validate_quotes(cls, v: list[Quote]) -> list[Quote]:
        """Validate quotes list - allow empty list for flexibility."""
        return v

    @model_validator(mode="before")
    @classmethod
    def set_updated_at(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Update the updated_at timestamp on any modification."""
        values["updated_at"] = datetime.now()
        return values

    # =========================================================================
    # Methods
    # =========================================================================

    def get_searchable_text(self) -> str:
        """Combine all searchable content fields into one text block.

        Used for BM25 full-text indexing. Combines abstract, question, method,
        gaps, results, interpretation, claims, full_text, and quote texts.

        Returns:
            Combined text from all content fields for BM25 indexing.

        Example:
            >>> text = media.get_searchable_text()
            >>> len(text) > 0
            True
        """
        parts = [
            self.abstract,
            self.question,
            self.method,
            self.gaps,
            self.results,
            self.interpretation,
            self.claims,
            self.full_text,
        ]
        # Add quote texts
        for quote in self.quotes:
            parts.append(quote.text)
        return "\n\n".join(parts)

    def to_bibtex(self) -> str:
        """Export media as bibtex entry.

        Generates a properly formatted bibtex entry based on media type:
        - @misc for video and podcast
        - @online for blog

        Returns:
            Bibtex formatted string ready for .bib file.

        Example:
            >>> bibtex = media.to_bibtex()
            >>> bibtex.startswith("@misc{") or bibtex.startswith("@online{")
            True
        """
        if self.media_type == MediaType.BLOG:
            return self._to_bibtex_online()
        else:
            return self._to_bibtex_misc()

    def _to_bibtex_misc(self) -> str:
        """Export as @misc entry for video/podcast."""
        lines = [f"@misc{{{self.id},"]
        lines.append(f"  author = {{{self.author}}},")
        lines.append(f"  title = {{{self.title}}},")
        lines.append(f"  year = {{{self.year}}},")

        if self.media_type == MediaType.VIDEO:
            howpublished = "YouTube video" if self.platform.lower() == "youtube" else "Video"
            if self.platform and self.platform.lower() != "youtube":
                howpublished = f"{self.platform} video"
        else:
            howpublished = "Podcast"

        lines.append(f"  howpublished = {{{howpublished}}},")
        lines.append(f"  url = {{{self.url}}},")
        lines.append(f"  urldate = {{{self.access_date}}},")

        # Build note field
        note_parts = []
        if self.media_type == MediaType.VIDEO:
            if self.channel:
                note_parts.append(self.channel)
            if self.duration:
                note_parts.append(f"Duration: {self.duration}")
        elif self.media_type == MediaType.PODCAST:
            if self.show_name:
                note_parts.append(self.show_name)
            if self.episode:
                note_parts.append(f"Episode {self.episode}")
            if self.host:
                note_parts.append(f"Host: {self.host}")
            if self.duration:
                note_parts.append(f"Duration: {self.duration}")

        if self.ai_generated:
            ai_note = "AI-generated content"
            if self.ai_provider:
                ai_note += f" using {self.ai_provider}"
                if self.ai_model:
                    ai_note += f" {self.ai_model}"
            note_parts.append(ai_note)

        if note_parts:
            lines.append(f"  note = {{{', '.join(note_parts)}}},")

        lines.append(f"  keywords = {{{self.keywords}}}")
        lines.append("}")
        return "\n".join(lines)

    def _to_bibtex_online(self) -> str:
        """Export as @online entry for blog."""
        lines = [f"@online{{{self.id},"]
        lines.append(f"  author = {{{self.author}}},")
        lines.append(f"  title = {{{self.title}}},")
        lines.append(f"  year = {{{self.year}}},")
        lines.append(f"  url = {{{self.url}}},")
        lines.append(f"  urldate = {{{self.access_date}}},")

        if self.website:
            lines.append(f"  organization = {{{self.website}}},")

        # Build note field for AI tracking
        if self.ai_generated:
            ai_note = "AI-generated content"
            if self.ai_provider:
                ai_note += f" using {self.ai_provider}"
                if self.ai_model:
                    ai_note += f" {self.ai_model}"
            lines.append(f"  note = {{{ai_note}}},")

        lines.append(f"  keywords = {{{self.keywords}}}")
        lines.append("}")
        return "\n".join(lines)


# =============================================================================
# Field Lists for CLI and API
# =============================================================================

# Paper field lists
PAPER_BIBTEX_FIELDS = [
    "author",
    "title",
    "year",
    "journal",
    "volume",
    "number",
    "issue",
    "pages",
    "publisher",
    "doi",
    "url",
    "file_path_pdf",
    "file_path_markdown",
    "keywords",
    "rating",
    "peer_reviewed",
    "ai_generated",
    "ai_provider",
    "ai_model",
]

PAPER_CONTENT_FIELDS = [
    "abstract",
    "question",
    "method",
    "gaps",
    "results",
    "interpretation",
    "claims",
    "full_text",
]

PAPER_ALL_FIELDS = PAPER_BIBTEX_FIELDS + PAPER_CONTENT_FIELDS

# Book field lists
BOOK_BIBTEX_FIELDS = [
    "author",
    "title",
    "year",
    "pages",
    "publisher",
    "url",
    "isbn",
    "chapter",
    "file_path_pdf",
    "file_path_markdown",
    "keywords",
    "ai_generated",
    "ai_provider",
    "ai_model",
]

BOOK_CONTENT_FIELDS = [
    "abstract",
    "question",
    "method",
    "gaps",
    "results",
    "interpretation",
    "claims",
    "full_text",
]

BOOK_ALL_FIELDS = BOOK_BIBTEX_FIELDS + BOOK_CONTENT_FIELDS

# Media field lists
MEDIA_BIBTEX_FIELDS = [
    "media_type",
    "author",
    "title",
    "year",
    "url",
    "access_date",
    "keywords",
    "rating",
    "platform",
    "channel",
    "duration",
    "video_id",
    "show_name",
    "episode",
    "season",
    "host",
    "guest",
    "website",
    "last_updated",
    "file_path_markdown",
    "file_path_pdf",
    "file_path_media",
    "ai_generated",
    "ai_provider",
    "ai_model",
]

MEDIA_CONTENT_FIELDS = [
    "abstract",
    "question",
    "method",
    "gaps",
    "results",
    "interpretation",
    "claims",
    "full_text",
]

MEDIA_ALL_FIELDS = MEDIA_BIBTEX_FIELDS + MEDIA_CONTENT_FIELDS

# Legacy aliases for backward compatibility
BIBTEX_FIELDS = PAPER_BIBTEX_FIELDS
CONTENT_FIELDS = PAPER_CONTENT_FIELDS
ALL_FIELDS = PAPER_ALL_FIELDS


# =============================================================================
# Vector Index Metadata Model
# =============================================================================


class VectorIndexMetadata(BaseModel):
    """Metadata for a named vector index.

    Each vector index stores embeddings for semantic search with a specific
    embedding model and configuration. This metadata tracks the index
    configuration and statistics.

    Attributes:
        name: Unique index name (e.g., "nova-1024", "titan-v2").
        embedding_model: Model ID for generating embeddings.
        dimensions: Vector dimensions (model-dependent).
        chunk_size: Number of words per chunk.
        chunk_overlap: Overlap words between chunks.
        chunk_count: Total chunks in the index.
        total_tokens: Total tokens processed.
        estimated_cost_usd: Estimated embedding cost.
        created_at: Index creation timestamp.
        updated_at: Last update timestamp.

    Example:
        >>> metadata = VectorIndexMetadata(
        ...     name="nova-1024",
        ...     embedding_model="amazon.nova-2-multimodal-embeddings-v1:0",
        ...     dimensions=1024,
        ... )
    """

    name: str = Field(description="Unique index name (e.g., 'nova-1024', 'titan-v2')")
    embedding_model: str = Field(description="AWS Bedrock model ID for embeddings")
    dimensions: int = Field(description="Vector dimensions for this index")
    chunk_size: int = Field(default=300, description="Number of words per chunk")
    chunk_overlap: int = Field(default=50, description="Overlap words between chunks")
    chunk_count: int = Field(default=0, description="Total number of chunks in index")
    total_tokens: int = Field(default=0, description="Total tokens processed")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated embedding cost in USD")
    created_at: datetime = Field(default_factory=datetime.now, description="When index was created")
    updated_at: datetime = Field(
        default_factory=datetime.now, description="When index was last updated"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate index name format (alphanumeric, hyphens, underscores)."""
        pattern = r"^[a-z0-9][a-z0-9_-]*$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid index name: '{v}'. "
                f"Name must start with letter/digit and contain only "
                f"lowercase letters, digits, hyphens, and underscores."
            )
        return v

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        """Validate dimensions is a positive integer."""
        if v <= 0:
            raise ValueError(f"Dimensions must be positive, got {v}.")
        return v


# =============================================================================
# Settings Model
# =============================================================================


class Settings(BaseModel):
    """Global settings for paper-index-tool.

    Stores user preferences and default configurations that persist
    across CLI sessions.

    Attributes:
        default_vector_index: Name of the default vector index for semantic search.

    Example:
        >>> settings = Settings(default_vector_index="nova-1024")
    """

    default_vector_index: str | None = Field(
        default=None, description="Default vector index for semantic search"
    )
