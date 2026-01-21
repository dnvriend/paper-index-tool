"""CLI entry point for paper-index-tool.

This module provides a comprehensive CLI for managing academic papers and books.
Commands are organized into subcommand groups (paper, book) and utility commands
(stats, export, import, query, reindex).

Command Structure:
    paper-index-tool
    ├── paper (subcommand group)
    │   ├── create, show, update, delete
    │   ├── abstract, question, method, gaps, results, claims, quotes
    │   ├── file-path-pdf, file-path-md, bibtex
    │   └── list
    ├── book (subcommand group)
    │   └── (same as paper)
    ├── stats, export, import, create-from-json, update-from-json
    ├── query, reindex
    └── completion

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import atexit
import json
from collections import Counter
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import typer

from paper_index_tool.completion import completion_app
from paper_index_tool.logging_config import get_logger, setup_logging
from paper_index_tool.models import Book, Media, MediaType, Paper, Quote
from paper_index_tool.storage import (
    BookRegistry,
    EntryExistsError,
    EntryNotFoundError,
    MediaRegistry,
    PaperRegistry,
)
from paper_index_tool.telemetry import TelemetryConfig, TelemetryService, traced

logger = get_logger(__name__)

app = typer.Typer(invoke_without_command=True)
paper_app = typer.Typer(
    help="Manage academic papers: create, read, update, delete, query fields, export bibtex"
)
book_app = typer.Typer(
    help="Manage books and chapters: create, read, update, delete, query fields, export bibtex"
)
media_app = typer.Typer(
    help="Manage media (video, podcast, blog): create, read, update, delete, query fields"
)


class OutputFormat(str, Enum):
    """Output format options."""

    HUMAN = "human"
    JSON = "json"


# =============================================================================
# Version Callback
# =============================================================================


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo("paper-index-tool version 0.1.0")
        raise typer.Exit()


def _shutdown_telemetry() -> None:
    """Shutdown telemetry on exit."""
    TelemetryService.get_instance().shutdown()


# =============================================================================
# Helper Functions - Paper
# =============================================================================


def _print_paper_summary(paper: Paper, output_format: OutputFormat) -> None:
    """Print paper summary in the requested format."""
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(paper.model_dump(mode="json"), indent=2))
    else:
        typer.echo(f"[{paper.id}]: {paper.title or 'No title'}")
        if paper.author:
            typer.echo(f"  Author: {paper.author}")
        if paper.year:
            typer.echo(f"  Year: {paper.year}")
        if paper.abstract:
            abstract = paper.abstract[:150] + "..." if len(paper.abstract) > 150 else paper.abstract
            typer.echo(f"  {abstract}")


def _truncate_to_words(text: str, max_words: int = 300) -> tuple[str, int]:
    """Truncate text to a maximum number of words.

    Args:
        text: The text to truncate.
        max_words: Maximum number of words to keep.

    Returns:
        Tuple of (truncated_text, total_word_count).
    """
    words = text.split()
    total_words = len(words)
    if total_words <= max_words:
        return text, total_words
    truncated = " ".join(words[:max_words]) + "..."
    return truncated, total_words


def _print_paper_detail(paper: Paper, output_format: OutputFormat) -> None:
    """Print full paper details in the requested format."""
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(paper.model_dump(mode="json"), indent=2))
    else:
        typer.echo(f"[{paper.id}]")
        typer.echo(f"{'=' * 60}")

        # Bibtex fields
        if paper.title:
            typer.echo(f"Title: {paper.title}")
        if paper.author:
            typer.echo(f"Author: {paper.author}")
        if paper.year:
            typer.echo(f"Year: {paper.year}")
        if paper.journal:
            typer.echo(f"Journal: {paper.journal}")
        if paper.volume:
            typer.echo(f"Volume: {paper.volume}")
        if paper.number:
            typer.echo(f"Number: {paper.number}")
        if paper.issue:
            typer.echo(f"Issue: {paper.issue}")
        if paper.pages:
            typer.echo(f"Pages: {paper.pages}")
        if paper.publisher:
            typer.echo(f"Publisher: {paper.publisher}")
        if paper.doi:
            typer.echo(f"DOI: {paper.doi}")
        if paper.url:
            typer.echo(f"URL: {paper.url}")
        if paper.file_path_pdf:
            typer.echo(f"PDF: {paper.file_path_pdf}")
        if paper.file_path_markdown:
            typer.echo(f"Markdown: {paper.file_path_markdown}")
        if paper.keywords:
            typer.echo(f"Keywords: {paper.keywords}")
        if paper.rating:
            typer.echo(f"Rating: {'*' * paper.rating}")
        typer.echo(f"Peer Reviewed: {paper.peer_reviewed}")

        # Content fields
        if paper.abstract:
            typer.echo(f"\n--- Abstract ---\n{paper.abstract}")
        if paper.question:
            typer.echo(f"\n--- Research Question ---\n{paper.question}")
        if paper.method:
            typer.echo(f"\n--- Method ---\n{paper.method}")
        if paper.gaps:
            typer.echo(f"\n--- Gaps ---\n{paper.gaps}")
        if paper.results:
            typer.echo(f"\n--- Results ---\n{paper.results}")
        if paper.interpretation:
            typer.echo(f"\n--- Interpretation ---\n{paper.interpretation}")
        if paper.claims:
            typer.echo(f"\n--- Claims ---\n{paper.claims}")
        if paper.quotes:
            typer.echo("\n--- Quotes ---")
            for i, q in enumerate(paper.quotes, 1):
                typer.echo(f'  [{i}] "{q.text}" (p. {q.page})')
        if paper.full_text:
            truncated, total_words = _truncate_to_words(paper.full_text, 300)
            typer.echo(f"\n--- Full Text ({total_words} words) ---")
            typer.echo(truncated)


def _get_paper_or_exit(paper_id: str) -> Paper:
    """Get paper by ID or exit with error."""
    registry = PaperRegistry()
    try:
        paper = registry.get_paper(paper_id)
        if not paper:
            raise EntryNotFoundError("paper", paper_id)
        return paper
    except EntryNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def _print_field(
    entry_id: str, field_name: str, value: str | None, output_format: OutputFormat
) -> None:
    """Print a single field value."""
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({field_name: value, "id": entry_id}))
    else:
        if value:
            typer.echo(value)
        else:
            typer.echo(f"No {field_name} set for entry '{entry_id}'")


# =============================================================================
# Helper Functions - Book
# =============================================================================


def _print_book_summary(book: Book, output_format: OutputFormat) -> None:
    """Print book summary in the requested format."""
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(book.model_dump(mode="json"), indent=2))
    else:
        typer.echo(f"[{book.id}]: {book.title or 'No title'}")
        if book.author:
            typer.echo(f"  Author: {book.author}")
        if book.year:
            typer.echo(f"  Year: {book.year}")
        if book.chapter:
            typer.echo(f"  Chapter: {book.chapter}")
        if book.abstract:
            abstract = book.abstract[:150] + "..." if len(book.abstract) > 150 else book.abstract
            typer.echo(f"  {abstract}")


def _print_book_detail(book: Book, output_format: OutputFormat) -> None:
    """Print full book details in the requested format."""
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(book.model_dump(mode="json"), indent=2))
    else:
        typer.echo(f"[{book.id}]")
        typer.echo(f"{'=' * 60}")

        # Bibtex fields
        if book.title:
            typer.echo(f"Title: {book.title}")
        if book.author:
            typer.echo(f"Author: {book.author}")
        if book.year:
            typer.echo(f"Year: {book.year}")
        if book.chapter:
            typer.echo(f"Chapter: {book.chapter}")
        if book.pages:
            typer.echo(f"Pages: {book.pages}")
        if book.publisher:
            typer.echo(f"Publisher: {book.publisher}")
        if book.isbn:
            typer.echo(f"ISBN: {book.isbn}")
        if book.url:
            typer.echo(f"URL: {book.url}")
        if book.file_path_pdf:
            typer.echo(f"PDF: {book.file_path_pdf}")
        if book.file_path_markdown:
            typer.echo(f"Markdown: {book.file_path_markdown}")
        if book.keywords:
            typer.echo(f"Keywords: {book.keywords}")

        # Content fields
        if book.abstract:
            typer.echo(f"\n--- Abstract ---\n{book.abstract}")
        if book.question:
            typer.echo(f"\n--- Question ---\n{book.question}")
        if book.method:
            typer.echo(f"\n--- Method ---\n{book.method}")
        if book.gaps:
            typer.echo(f"\n--- Gaps ---\n{book.gaps}")
        if book.results:
            typer.echo(f"\n--- Results ---\n{book.results}")
        if book.interpretation:
            typer.echo(f"\n--- Interpretation ---\n{book.interpretation}")
        if book.claims:
            typer.echo(f"\n--- Claims ---\n{book.claims}")
        if book.quotes:
            typer.echo("\n--- Quotes ---")
            for i, q in enumerate(book.quotes, 1):
                typer.echo(f'  [{i}] "{q.text}" (p. {q.page})')
        if book.full_text:
            truncated, total_words = _truncate_to_words(book.full_text, 300)
            typer.echo(f"\n--- Full Text ({total_words} words) ---")
            typer.echo(truncated)


def _get_book_or_exit(book_id: str) -> Book:
    """Get book by ID or exit with error."""
    registry = BookRegistry()
    try:
        book = registry.get_book(book_id)
        if not book:
            raise EntryNotFoundError("book", book_id)
        return book
    except EntryNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


def _get_book_or_chapters_or_exit(book_id: str) -> Book | list[Book]:
    """Get book by ID, or all chapters if basename given, or exit with error.

    This function provides smart lookup:
    1. First tries exact match for book_id
    2. If not found and book_id has no ch<n> suffix, searches for chapters

    Args:
        book_id: Book ID or basename to look up.

    Returns:
        Single Book if exact match found, or list of Books if chapters found.

    Raises:
        typer.Exit: If nothing found.
    """
    registry = BookRegistry()
    result = registry.get_book_or_chapters(book_id)

    if result is None:
        typer.echo(
            f"Error: Book '{book_id}' not found. "
            f"Use 'paper-index-tool book list' to see available books.",
            err=True,
        )
        raise typer.Exit(1)

    return result


def _merge_chapters_to_dict(chapters: list[Book], basename: str) -> dict[str, Any]:
    """Merge multiple chapter Book objects into a single dict.

    Fields are merged according to their type:
    - Single value fields: taken from first chapter (id uses basename)
    - Text content fields: concatenated with [chN] headers
    - Comma-separated fields: joined with commas
    - List fields (quotes): flattened/appended

    Args:
        chapters: List of Book objects (chapters) sorted by chapter number.
        basename: The basename to use as the merged ID.

    Returns:
        Merged dictionary suitable for JSON output.
    """
    if not chapters:
        return {}

    first = chapters[0]

    # Single value fields - take from first chapter
    merged: dict[str, Any] = {
        "id": basename,
        "author": first.author,
        "title": first.title,
        "year": first.year,
        "pages": first.pages,
        "publisher": first.publisher,
        "url": first.url,
        "isbn": first.isbn,
        "created_at": first.created_at.isoformat() if first.created_at else None,
        "updated_at": first.updated_at.isoformat() if first.updated_at else None,
        "ai_generated": first.ai_generated,
        "ai_provider": first.ai_provider,
        "ai_model": first.ai_model,
    }

    # Comma-separated fields
    comma_fields = ["chapter", "file_path_pdf", "file_path_markdown", "keywords"]
    for field in comma_fields:
        values = [getattr(ch, field, "") or "" for ch in chapters]
        # Filter empty values and join with comma
        non_empty = [v for v in values if v]
        merged[field] = ", ".join(non_empty)

    # Text content fields - concat with [chN] headers
    text_fields = [
        "abstract",
        "question",
        "method",
        "gaps",
        "results",
        "interpretation",
        "claims",
        "full_text",
    ]
    for field in text_fields:
        parts = []
        for ch in chapters:
            value = getattr(ch, field, "") or ""
            if value:
                # Extract chapter number from ID (e.g., vogelgesang2023ch1 -> ch1)
                ch_suffix = ch.id.replace(basename, "")
                parts.append(f"[{ch_suffix}]\n{value}")
        merged[field] = "\n\n".join(parts)

    # Quotes - flatten all quotes from all chapters
    all_quotes = []
    for ch in chapters:
        if ch.quotes:
            for q in ch.quotes:
                all_quotes.append(q.model_dump())
    merged["quotes"] = all_quotes

    return merged


def _print_chapters_sequential(chapters: list[Book], output_format: OutputFormat) -> None:
    """Print multiple chapters sequentially with separators.

    Args:
        chapters: List of Book objects (chapters) to print.
        output_format: Output format (HUMAN or JSON).
    """
    if output_format == OutputFormat.JSON:
        # For JSON, output as single merged object
        basename = BookRegistry.get_basename(chapters[0].id) if chapters else "unknown"
        merged = _merge_chapters_to_dict(chapters, basename)
        typer.echo(json.dumps(merged, indent=2))
    else:
        total = len(chapters)
        for i, chapter in enumerate(chapters, 1):
            typer.echo(f"{'=' * 60}")
            typer.echo(f"Chapter {i} of {total}: {chapter.id}")
            typer.echo(f"{'=' * 60}")
            _print_book_detail(chapter, OutputFormat.HUMAN)
            if i < total:
                typer.echo("")  # Blank line between chapters


def _print_chapters_field(
    chapters: list[Book],
    field_name: str,
    output_format: OutputFormat,
) -> None:
    """Print a field from multiple chapters with headers.

    Args:
        chapters: List of Book objects (chapters).
        field_name: Field name to extract (e.g., 'abstract', 'quotes').
        output_format: Output format (HUMAN or JSON).
    """
    if output_format == OutputFormat.JSON:
        # Return merged single object for JSON
        basename = BookRegistry.get_basename(chapters[0].id) if chapters else "unknown"
        merged = _merge_chapters_to_dict(chapters, basename)
        # Output only the requested field
        typer.echo(json.dumps({"id": basename, field_name: merged.get(field_name)}, indent=2))
    else:
        has_any_content = False
        for chapter in chapters:
            value = getattr(chapter, field_name, None)
            if value:
                has_any_content = True
                typer.echo(f"[{chapter.id}]")
                if field_name == "quotes" and isinstance(value, list):
                    for i, q in enumerate(value, 1):
                        typer.echo(f'  [{i}] "{q.text}" (p. {q.page})')
                else:
                    typer.echo(value)
                typer.echo("")  # Blank line between chapters

        if not has_any_content:
            basename = BookRegistry.get_basename(chapters[0].id) if chapters else "unknown"
            typer.echo(f"No {field_name} set for any chapter in '{basename}'")


# =============================================================================
# Helper Functions - Media
# =============================================================================


def _print_media_summary(media: Media, output_format: OutputFormat) -> None:
    """Print media summary in the requested format."""
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(media.model_dump(mode="json"), indent=2))
    else:
        typer.echo(f"[{media.id}]: {media.title or 'No title'}")
        if media.author:
            typer.echo(f"  Author: {media.author}")
        if media.year:
            typer.echo(f"  Year: {media.year}")
        typer.echo(f"  Type: {media.media_type.value}")
        if media.abstract:
            abstract = media.abstract[:150] + "..." if len(media.abstract) > 150 else media.abstract
            typer.echo(f"  {abstract}")


def _print_media_detail(media: Media, output_format: OutputFormat) -> None:
    """Print full media details in the requested format."""
    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(media.model_dump(mode="json"), indent=2))
    else:
        typer.echo(f"[{media.id}]")
        typer.echo(f"{'=' * 60}")

        # Core fields
        if media.title:
            typer.echo(f"Title: {media.title}")
        if media.author:
            typer.echo(f"Author: {media.author}")
        if media.year:
            typer.echo(f"Year: {media.year}")
        typer.echo(f"Type: {media.media_type.value}")
        if media.url:
            typer.echo(f"URL: {media.url}")
        if media.access_date:
            typer.echo(f"Access Date: {media.access_date}")

        # Video-specific fields
        if media.media_type == MediaType.VIDEO:
            if media.platform:
                typer.echo(f"Platform: {media.platform}")
            if media.channel:
                typer.echo(f"Channel: {media.channel}")
            if media.duration:
                typer.echo(f"Duration: {media.duration}")
            if media.video_id:
                typer.echo(f"Video ID: {media.video_id}")

        # Podcast-specific fields
        if media.media_type == MediaType.PODCAST:
            if media.show_name:
                typer.echo(f"Show: {media.show_name}")
            if media.episode:
                typer.echo(f"Episode: {media.episode}")
            if media.season:
                typer.echo(f"Season: {media.season}")
            if media.host:
                typer.echo(f"Host: {media.host}")
            if media.guest:
                typer.echo(f"Guest: {media.guest}")
            if media.duration:
                typer.echo(f"Duration: {media.duration}")

        # Blog-specific fields
        if media.media_type == MediaType.BLOG:
            if media.website:
                typer.echo(f"Website: {media.website}")
            if media.last_updated:
                typer.echo(f"Last Updated: {media.last_updated}")

        # File paths
        if media.file_path_markdown:
            typer.echo(f"Markdown: {media.file_path_markdown}")
        if media.file_path_pdf:
            typer.echo(f"PDF: {media.file_path_pdf}")
        if media.file_path_media:
            typer.echo(f"Media File: {media.file_path_media}")

        # Common metadata
        if media.keywords:
            typer.echo(f"Keywords: {media.keywords}")
        if media.rating:
            typer.echo(f"Rating: {'*' * media.rating}")

        # AI tracking
        if media.ai_generated:
            typer.echo("AI Generated: Yes")
            if media.ai_provider:
                typer.echo(f"AI Provider: {media.ai_provider}")
            if media.ai_model:
                typer.echo(f"AI Model: {media.ai_model}")

        # Content fields
        if media.abstract:
            typer.echo(f"\n--- Abstract ---\n{media.abstract}")
        if media.question:
            typer.echo(f"\n--- Question ---\n{media.question}")
        if media.method:
            typer.echo(f"\n--- Method ---\n{media.method}")
        if media.gaps:
            typer.echo(f"\n--- Gaps ---\n{media.gaps}")
        if media.results:
            typer.echo(f"\n--- Results ---\n{media.results}")
        if media.interpretation:
            typer.echo(f"\n--- Interpretation ---\n{media.interpretation}")
        if media.claims:
            typer.echo(f"\n--- Claims ---\n{media.claims}")
        if media.quotes:
            typer.echo("\n--- Quotes ---")
            for i, q in enumerate(media.quotes, 1):
                if q.timestamp:
                    typer.echo(f'  [{i}] "{q.text}" ({q.timestamp})')
                elif q.page:
                    typer.echo(f'  [{i}] "{q.text}" (p. {q.page})')
                else:
                    typer.echo(f'  [{i}] "{q.text}"')
        if media.full_text:
            truncated, total_words = _truncate_to_words(media.full_text, 300)
            typer.echo(f"\n--- Full Text ({total_words} words) ---")
            typer.echo(truncated)


def _get_media_or_exit(media_id: str) -> Media:
    """Get media by ID or exit with error."""
    registry = MediaRegistry()
    try:
        media = registry.get_media(media_id)
        if not media:
            raise EntryNotFoundError("media", media_id)
        return media
    except EntryNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


# =============================================================================
# Main App Callback
# =============================================================================


@traced("main")
def _run_main_command() -> None:
    """Execute main command logic with tracing."""
    logger.info("paper-index-tool started")
    typer.echo("paper-index-tool - Academic paper and book index management")
    typer.echo("Use --help for available commands")
    logger.info("paper-index-tool completed")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Verbosity level: -v=INFO, -vv=DEBUG, -vvv=TRACE (includes library internals)",
        ),
    ] = 0,
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
    telemetry: Annotated[
        bool,
        typer.Option(
            "--telemetry",
            envvar="OTEL_ENABLED",
            help="Enable OpenTelemetry tracing (or set OTEL_ENABLED=true)",
        ),
    ] = False,
) -> None:
    """Academic paper, book, and media index management tool with BM25 search.

    \b
    SUBCOMMANDS:
        paper       Manage academic papers (CRUD, field queries, bibtex export)
        book        Manage books and chapters (CRUD, field queries, bibtex export)
        media       Manage media entries: video, podcast, blog (CRUD, field queries)
        stats       Show statistics (counts by author, year, keywords)
        query       BM25 full-text search across all entries
        reindex     Rebuild search index after bulk operations
        export      Export all data to JSON backup file
        import      Import data from JSON backup file

    \b
    QUICK START:
        paper-index-tool paper create ashford2012 --title "Developing as a leader" ...
        paper-index-tool paper show ashford2012
        paper-index-tool query "leadership identity" --all
        paper-index-tool stats

    \b
    DATA STORAGE:
        ~/.config/paper-index-tool/papers.json   - Paper entries
        ~/.config/paper-index-tool/books.json    - Book entries
        ~/.config/paper-index-tool/media.json    - Media entries
        ~/.config/paper-index-tool/bm25s/        - Search index
    """
    setup_logging(verbose)

    # Initialize telemetry
    config = TelemetryConfig.from_env()
    config.enabled = telemetry or config.enabled
    TelemetryService.get_instance().initialize(config)
    atexit.register(_shutdown_telemetry)

    if ctx.invoked_subcommand is None:
        _run_main_command()


# =============================================================================
# PAPER Commands
# =============================================================================


@paper_app.command(name="create")
def paper_create(
    paper_id: Annotated[str, typer.Argument(help="Unique paper ID (e.g., ashford2012)")],
    # Bibtex fields
    author: Annotated[str, typer.Option("--author", help="Author(s)")],
    title: Annotated[str, typer.Option("--title", help="Paper title")],
    year: Annotated[int, typer.Option("--year", help="Publication year")],
    journal: Annotated[str, typer.Option("--journal", help="Journal name")],
    volume: Annotated[str, typer.Option("--volume", help="Volume number")],
    number: Annotated[str, typer.Option("--number", help="Journal number")],
    issue: Annotated[str, typer.Option("--issue", help="Issue number")],
    pages: Annotated[str, typer.Option("--pages", help="Page range")],
    publisher: Annotated[str, typer.Option("--publisher", help="Publisher")],
    doi: Annotated[str, typer.Option("--doi", help="DOI")],
    file_path_pdf: Annotated[str, typer.Option("--file-path-pdf", help="Path to PDF")],
    file_path_markdown: Annotated[str, typer.Option("--file-path-md", help="Path to markdown")],
    keywords: Annotated[str, typer.Option("--keywords", help="Comma-separated keywords")],
    rating: Annotated[int, typer.Option("--rating", min=1, max=5, help="Quality rating 1-5")],
    peer_reviewed: Annotated[bool, typer.Option("--peer-reviewed", help="Is peer-reviewed")],
    # Content fields
    abstract: Annotated[str, typer.Option("--abstract", help="Paper abstract")],
    question: Annotated[str, typer.Option("--question", help="Research question")],
    method: Annotated[str, typer.Option("--method", help="Research method")],
    gaps: Annotated[str, typer.Option("--gaps", help="Identified gaps")],
    results: Annotated[str, typer.Option("--results", help="Key results")],
    interpretation: Annotated[str, typer.Option("--interpretation", help="Interpretation")],
    claims: Annotated[str, typer.Option("--claims", help="Key claims/findings")],
    full_text: Annotated[str, typer.Option("--full-text", help="Full paper content")],
    # Optional fields
    url: Annotated[str | None, typer.Option("--url", help="URL")] = None,
    quotes_json: Annotated[
        str | None, typer.Option("--quotes", help="Quotes as JSON array")
    ] = None,
    # Output
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Create a new paper entry with all metadata and content fields.

    \b
    REQUIRED FIELDS (bibtex metadata):
        --author        Author(s) in "Last, First" format
        --title         Paper title
        --year          Publication year (4 digits)
        --journal       Journal name
        --volume        Volume number
        --number        Journal number
        --issue         Issue number
        --pages         Page range (e.g., "46-56")
        --publisher     Publisher name
        --doi           Digital Object Identifier

    \b
    REQUIRED FIELDS (content - for search and citation validation):
        --abstract      Paper abstract (verbatim from paper)
        --question      Research question(s)
        --method        Research methodology
        --gaps          Identified limitations/gaps
        --results       Key findings
        --interpretation Discussion/implications
        --claims        Key verifiable claims
        --full-text     Full paper content (for BM25 search)

    \b
    OPTIONAL FIELDS:
        --url           URL to paper
        --quotes        Quotes as JSON array: [{"text": "...", "page": 1}]

    \b
    EXAMPLES:
        # Minimal create (use create-from-json for easier bulk entry)
        paper-index-tool paper create ashford2012 \\
            --author "Ashford, S. J." --title "Developing as a leader" \\
            --year 2012 --journal "Organizational Dynamics" ...

        # Recommended: Use JSON file for complex entries
        paper-index-tool create-from-json ashford2012.json

    \b
    OUTPUT FORMATS:
        --format human  Human-readable (default)
        --format json   JSON for scripting: {"status": "created", "id": "..."}
    """
    logger.info("Creating paper: %s", paper_id)

    registry = PaperRegistry()

    # Check if exists
    if registry.paper_exists(paper_id):
        typer.echo(
            f"Error: Paper '{paper_id}' already exists. "
            f"Use 'paper-index-tool paper update {paper_id}' to modify or "
            f"'paper-index-tool paper delete {paper_id}' to remove first.",
            err=True,
        )
        raise typer.Exit(1)

    # Parse quotes
    quotes: list[Quote] = []
    if quotes_json:
        try:
            quotes_data = json.loads(quotes_json)
            quotes = [Quote(**q) for q in quotes_data]
        except (json.JSONDecodeError, TypeError) as e:
            typer.echo(
                f"Error: Invalid quotes JSON: {e}. "
                f'Expected format: [{{"text": "quote text", "page": 1}}]',
                err=True,
            )
            raise typer.Exit(1)

    # Create paper
    try:
        paper = Paper(
            id=paper_id,
            author=author,
            title=title,
            year=year,
            journal=journal,
            volume=volume,
            number=number,
            issue=issue,
            pages=pages,
            publisher=publisher,
            doi=doi,
            url=url,
            file_path_pdf=file_path_pdf,
            file_path_markdown=file_path_markdown,
            keywords=keywords,
            rating=rating,
            peer_reviewed=peer_reviewed,
            abstract=abstract,
            question=question,
            method=method,
            gaps=gaps,
            results=results,
            interpretation=interpretation,
            claims=claims,
            quotes=quotes,
            full_text=full_text,
        )
        registry.add_paper(paper)
    except EntryExistsError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: Validation failed: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "created", "id": paper_id}))
    else:
        typer.echo(f"Created paper: {paper_id}")


@paper_app.command(name="show")
def paper_show(
    paper_id: Annotated[str, typer.Argument(help="Paper ID to show")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show details of a paper.

    \b
    Examples:
        paper-index-tool paper show ashford2012
        paper-index-tool paper show ashford2012 --format json
    """
    logger.info("Showing paper: %s", paper_id)
    paper = _get_paper_or_exit(paper_id)
    _print_paper_detail(paper, output_format)


@paper_app.command(name="update")
def paper_update(
    paper_id: Annotated[str, typer.Argument(help="Paper ID to update")],
    # Bibtex fields
    author: Annotated[str | None, typer.Option("--author", help="Author(s)")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Paper title")] = None,
    year: Annotated[int | None, typer.Option("--year", help="Publication year")] = None,
    journal: Annotated[str | None, typer.Option("--journal", help="Journal name")] = None,
    volume: Annotated[str | None, typer.Option("--volume", help="Volume number")] = None,
    number: Annotated[str | None, typer.Option("--number", help="Journal number")] = None,
    issue: Annotated[str | None, typer.Option("--issue", help="Issue number")] = None,
    pages: Annotated[str | None, typer.Option("--pages", help="Page range")] = None,
    publisher: Annotated[str | None, typer.Option("--publisher", help="Publisher")] = None,
    doi: Annotated[str | None, typer.Option("--doi", help="DOI")] = None,
    url: Annotated[str | None, typer.Option("--url", help="URL")] = None,
    file_path_pdf: Annotated[
        str | None, typer.Option("--file-path-pdf", help="Path to PDF")
    ] = None,
    file_path_markdown: Annotated[
        str | None, typer.Option("--file-path-md", help="Path to markdown")
    ] = None,
    keywords: Annotated[
        str | None, typer.Option("--keywords", help="Comma-separated keywords")
    ] = None,
    rating: Annotated[
        int | None, typer.Option("--rating", min=1, max=5, help="Quality rating 1-5")
    ] = None,
    peer_reviewed: Annotated[
        bool | None, typer.Option("--peer-reviewed", help="Is peer-reviewed")
    ] = None,
    # Content fields
    abstract: Annotated[str | None, typer.Option("--abstract", help="Paper abstract")] = None,
    question: Annotated[str | None, typer.Option("--question", help="Research question")] = None,
    method: Annotated[str | None, typer.Option("--method", help="Research method")] = None,
    gaps: Annotated[str | None, typer.Option("--gaps", help="Identified gaps")] = None,
    results: Annotated[str | None, typer.Option("--results", help="Key results")] = None,
    interpretation: Annotated[
        str | None, typer.Option("--interpretation", help="Interpretation")
    ] = None,
    claims: Annotated[str | None, typer.Option("--claims", help="Key claims/findings")] = None,
    full_text: Annotated[str | None, typer.Option("--full-text", help="Full paper content")] = None,
    quotes_json: Annotated[
        str | None, typer.Option("--quotes", help="Quotes as JSON array")
    ] = None,
    # Output
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Update an existing paper.

    \b
    Only provided fields will be updated. Other fields remain unchanged.

    \b
    Examples:
        paper-index-tool paper update ashford2012 --rating 5
        paper-index-tool paper update ashford2012 --method "Updated method..."
    """
    logger.info("Updating paper: %s", paper_id)

    registry = PaperRegistry()

    # Build updates dict (only non-None values)
    updates: dict[str, object] = {}
    if author is not None:
        updates["author"] = author
    if title is not None:
        updates["title"] = title
    if year is not None:
        updates["year"] = year
    if journal is not None:
        updates["journal"] = journal
    if volume is not None:
        updates["volume"] = volume
    if number is not None:
        updates["number"] = number
    if issue is not None:
        updates["issue"] = issue
    if pages is not None:
        updates["pages"] = pages
    if publisher is not None:
        updates["publisher"] = publisher
    if doi is not None:
        updates["doi"] = doi
    if url is not None:
        updates["url"] = url
    if file_path_pdf is not None:
        updates["file_path_pdf"] = file_path_pdf
    if file_path_markdown is not None:
        updates["file_path_markdown"] = file_path_markdown
    if keywords is not None:
        updates["keywords"] = keywords
    if rating is not None:
        updates["rating"] = rating
    if peer_reviewed is not None:
        updates["peer_reviewed"] = peer_reviewed
    if abstract is not None:
        updates["abstract"] = abstract
    if question is not None:
        updates["question"] = question
    if method is not None:
        updates["method"] = method
    if gaps is not None:
        updates["gaps"] = gaps
    if results is not None:
        updates["results"] = results
    if interpretation is not None:
        updates["interpretation"] = interpretation
    if claims is not None:
        updates["claims"] = claims
    if full_text is not None:
        updates["full_text"] = full_text
    if quotes_json is not None:
        try:
            quotes_data = json.loads(quotes_json)
            updates["quotes"] = [Quote(**q).model_dump() for q in quotes_data]
        except (json.JSONDecodeError, TypeError) as e:
            typer.echo(
                f"Error: Invalid quotes JSON: {e}. "
                f'Expected format: [{{"text": "quote text", "page": 1}}]',
                err=True,
            )
            raise typer.Exit(1)

    if not updates:
        typer.echo(
            "No updates provided. Use --help to see available options.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        registry.update_paper(paper_id, updates)
    except EntryNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: Validation failed: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "updated", "id": paper_id}))
    else:
        typer.echo(f"Updated paper: {paper_id}")


@paper_app.command(name="delete")
def paper_delete(
    paper_id: Annotated[str, typer.Argument(help="Paper ID to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Delete a paper.

    \b
    Examples:
        paper-index-tool paper delete ashford2012
        paper-index-tool paper delete ashford2012 --force
    """
    logger.info("Deleting paper: %s", paper_id)

    registry = PaperRegistry()

    if not registry.paper_exists(paper_id):
        typer.echo(
            f"Error: Paper '{paper_id}' not found. "
            f"Use 'paper-index-tool paper list' to see available papers.",
            err=True,
        )
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete paper '{paper_id}'?")
        if not confirm:
            typer.echo("Cancelled")
            raise typer.Exit(0)

    try:
        registry.delete_paper(paper_id)
    except EntryNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "deleted", "id": paper_id}))
    else:
        typer.echo(f"Deleted paper: {paper_id}")


@paper_app.command(name="list")
def paper_list(
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
    count: Annotated[
        bool, typer.Option("--count", "-c", help="Show only the count of papers")
    ] = False,
) -> None:
    """List all papers.

    \b
    Examples:
        paper-index-tool paper list
        paper-index-tool paper list --format json
        paper-index-tool paper list --count
    """
    logger.info("Listing papers")

    registry = PaperRegistry()
    papers = registry.list_papers()

    if count:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"count": len(papers)}))
        else:
            typer.echo(len(papers))
        return

    if output_format == OutputFormat.JSON:
        papers_data = [p.model_dump(mode="json") for p in papers]
        typer.echo(json.dumps(papers_data, indent=2))
    else:
        if not papers:
            typer.echo("No papers indexed")
            return

        typer.echo(f"Found {len(papers)} paper(s):\n")
        for paper in papers:
            _print_paper_summary(paper, output_format)
            typer.echo()


@paper_app.command(name="clear")
def paper_clear(
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help="Confirm clearing all papers (required for safety)",
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Clear all papers from the index.

    This command removes all paper entries and clears the BM25 search index.
    Requires --approve flag for safety.

    \b
    Examples:
        # Preview what would be cleared
        paper-index-tool paper list

        # Clear all papers (requires --approve)
        paper-index-tool paper clear --approve
    """
    if not approve:
        typer.echo(
            "Error: This will permanently delete ALL papers. Use --approve flag to confirm.",
            err=True,
        )
        raise typer.Exit(1)

    logger.info("Clearing all papers")

    registry = PaperRegistry()
    count = registry.clear()

    # Clear the BM25 index for papers
    from paper_index_tool.search import PaperSearcher

    searcher = PaperSearcher()
    index_path = searcher.index_path
    if index_path.exists():
        import shutil

        shutil.rmtree(index_path)
        logger.info("Cleared paper search index at %s", index_path)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "cleared", "count": count}))
    else:
        typer.echo(f"Cleared {count} paper(s) and search index")


# Paper field query commands
@paper_app.command(name="abstract")
def paper_abstract(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show paper abstract.

    \b
    Examples:
        paper-index-tool paper abstract ashford2012
    """
    paper = _get_paper_or_exit(paper_id)
    _print_field(paper_id, "abstract", paper.abstract, output_format)


@paper_app.command(name="question")
def paper_question(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show research question.

    \b
    Examples:
        paper-index-tool paper question ashford2012
    """
    paper = _get_paper_or_exit(paper_id)
    _print_field(paper_id, "question", paper.question, output_format)


@paper_app.command(name="method")
def paper_method(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show research method.

    \b
    Examples:
        paper-index-tool paper method ashford2012
    """
    paper = _get_paper_or_exit(paper_id)
    _print_field(paper_id, "method", paper.method, output_format)


@paper_app.command(name="gaps")
def paper_gaps(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show identified gaps.

    \b
    Examples:
        paper-index-tool paper gaps ashford2012
    """
    paper = _get_paper_or_exit(paper_id)
    _print_field(paper_id, "gaps", paper.gaps, output_format)


@paper_app.command(name="results")
def paper_results(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show key results.

    \b
    Examples:
        paper-index-tool paper results ashford2012
    """
    paper = _get_paper_or_exit(paper_id)
    _print_field(paper_id, "results", paper.results, output_format)


@paper_app.command(name="claims")
def paper_claims(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show key claims/findings.

    \b
    Examples:
        paper-index-tool paper claims ashford2012
    """
    paper = _get_paper_or_exit(paper_id)
    _print_field(paper_id, "claims", paper.claims, output_format)


@paper_app.command(name="quotes")
def paper_quotes(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show stored quotes with page references.

    \b
    Examples:
        paper-index-tool paper quotes ashford2012
    """
    paper = _get_paper_or_exit(paper_id)

    if output_format == OutputFormat.JSON:
        quotes_data = [q.model_dump() for q in paper.quotes]
        typer.echo(json.dumps({"quotes": quotes_data, "id": paper_id}))
    else:
        if not paper.quotes:
            typer.echo(f"No quotes stored for paper '{paper_id}'")
            return

        for i, q in enumerate(paper.quotes, 1):
            typer.echo(f'[{i}] "{q.text}" (p. {q.page})')


@paper_app.command(name="add-quote")
def paper_add_quote(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    text: Annotated[str, typer.Argument(help="Quote text (verbatim)")],
    page: Annotated[int, typer.Argument(help="Page number")],
) -> None:
    """Add a quote to a paper.

    \b
    Examples:
        paper-index-tool paper add-quote ashford2012 "Leadership is a process..." 17
    """
    paper = _get_paper_or_exit(paper_id)
    registry = PaperRegistry()

    new_quote = Quote(text=text, page=page)
    updated_quotes = paper.quotes + [new_quote]

    registry.update_entry(paper_id, {"quotes": [q.model_dump() for q in updated_quotes]})
    typer.echo(f"Added quote to paper '{paper_id}' (page {page})")


@paper_app.command(name="file-path-pdf")
def paper_file_path_pdf(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show the PDF file path.

    \b
    Examples:
        paper-index-tool paper file-path-pdf ashford2012
    """
    paper = _get_paper_or_exit(paper_id)
    _print_field(paper_id, "file_path_pdf", paper.file_path_pdf, output_format)


@paper_app.command(name="file-path-md")
def paper_file_path_md(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show the markdown file path.

    \b
    Examples:
        paper-index-tool paper file-path-md ashford2012
    """
    paper = _get_paper_or_exit(paper_id)
    _print_field(paper_id, "file_path_markdown", paper.file_path_markdown, output_format)


@paper_app.command(name="bibtex")
def paper_bibtex(
    paper_id: Annotated[str, typer.Argument(help="Paper ID")],
) -> None:
    """Export paper as bibtex entry.

    \b
    Examples:
        paper-index-tool paper bibtex ashford2012
    """
    paper = _get_paper_or_exit(paper_id)
    typer.echo(paper.to_bibtex())


@paper_app.command(name="query")
def paper_query(
    paper_id: Annotated[str, typer.Argument(help="Paper ID to search")],
    search_query: Annotated[str, typer.Argument(help="Search query string")],
    fragments: Annotated[
        bool, typer.Option("--fragments", help="Show matching text fragments")
    ] = False,
    context: Annotated[int, typer.Option("-C", "--context", help="Context lines around match")] = 2,
    num_results: Annotated[int, typer.Option("-n", "--num", help="Number of results")] = 10,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Search within a single paper using BM25.

    \b
    Convenience command equivalent to: query "terms" --paper <id>

    \b
    Examples:
        paper-index-tool paper query cesinger2023 "narcissism commitment"
        paper-index-tool paper query ashford2012 "leadership identity" --fragments
    """
    # Delegate to main query command
    query_command(
        search_query=search_query,
        paper_id=paper_id,
        book_id=None,
        all_entries=False,
        fragments=fragments,
        context=context,
        num_results=num_results,
        output_format=output_format,
    )


# =============================================================================
# BOOK Commands
# =============================================================================


@book_app.command(name="create")
def book_create(
    book_id: Annotated[str, typer.Argument(help="Unique book ID (e.g., vogelgesang2023)")],
    # Bibtex fields
    author: Annotated[str, typer.Option("--author", help="Author(s)")],
    title: Annotated[str, typer.Option("--title", help="Book title")],
    year: Annotated[int, typer.Option("--year", help="Publication year")],
    pages: Annotated[str, typer.Option("--pages", help="Page range")],
    publisher: Annotated[str, typer.Option("--publisher", help="Publisher")],
    chapter: Annotated[str, typer.Option("--chapter", help="Chapter title/number")],
    file_path_pdf: Annotated[str, typer.Option("--file-path-pdf", help="Path to PDF")],
    file_path_markdown: Annotated[str, typer.Option("--file-path-md", help="Path to markdown")],
    keywords: Annotated[str, typer.Option("--keywords", help="Comma-separated keywords")],
    # Content fields
    abstract: Annotated[str, typer.Option("--abstract", help="Book abstract")],
    question: Annotated[str, typer.Option("--question", help="Main question/thesis")],
    method: Annotated[str, typer.Option("--method", help="Methodology/approach")],
    gaps: Annotated[str, typer.Option("--gaps", help="Identified gaps")],
    results: Annotated[str, typer.Option("--results", help="Key results")],
    interpretation: Annotated[str, typer.Option("--interpretation", help="Interpretation")],
    claims: Annotated[str, typer.Option("--claims", help="Key claims")],
    full_text: Annotated[str, typer.Option("--full-text", help="Full book/chapter content")],
    # Optional fields
    url: Annotated[str | None, typer.Option("--url", help="URL")] = None,
    isbn: Annotated[str | None, typer.Option("--isbn", help="ISBN")] = None,
    quotes_json: Annotated[
        str | None, typer.Option("--quotes", help="Quotes as JSON array")
    ] = None,
    # Output
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Create a new book entry.

    \b
    All bibtex and content fields are mandatory except url, isbn, and quotes.

    \b
    Examples:
        paper-index-tool book create vogelgesang2023 \\
            --author "Vogelgesang Lester, Gretchen" \\
            --title "Applied Organizational Behavior" \\
            --year 2023 --pages "1-50" --publisher "SAGE Publications" \\
            --chapter "Chapter 1" \\
            --file-path-pdf "/path/to/book.pdf" \\
            --file-path-md "/path/to/book.md" \\
            --keywords "leadership,identity" \\
            --abstract "This chapter examines..." \\
            --question "How do leaders develop..." \\
            --method "Case study approach..." \\
            --gaps "Limited generalizability..." \\
            --results "Key findings..." \\
            --interpretation "Results suggest..." \\
            --claims "Leadership identity..." \\
            --full-text "Full content here..."
    """
    logger.info("Creating book: %s", book_id)

    registry = BookRegistry()

    # Check if exists
    if registry.book_exists(book_id):
        typer.echo(
            f"Error: Book '{book_id}' already exists. "
            f"Use 'paper-index-tool book update {book_id}' to modify or "
            f"'paper-index-tool book delete {book_id}' to remove first.",
            err=True,
        )
        raise typer.Exit(1)

    # Parse quotes
    quotes: list[Quote] = []
    if quotes_json:
        try:
            quotes_data = json.loads(quotes_json)
            quotes = [Quote(**q) for q in quotes_data]
        except (json.JSONDecodeError, TypeError) as e:
            typer.echo(
                f"Error: Invalid quotes JSON: {e}. "
                f'Expected format: [{{"text": "quote text", "page": 1}}]',
                err=True,
            )
            raise typer.Exit(1)

    # Create book
    try:
        book = Book(
            id=book_id,
            author=author,
            title=title,
            year=year,
            pages=pages,
            publisher=publisher,
            url=url,
            isbn=isbn,
            chapter=chapter,
            file_path_pdf=file_path_pdf,
            file_path_markdown=file_path_markdown,
            keywords=keywords,
            abstract=abstract,
            question=question,
            method=method,
            gaps=gaps,
            results=results,
            interpretation=interpretation,
            claims=claims,
            quotes=quotes,
            full_text=full_text,
        )
        registry.add_book(book)
    except EntryExistsError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: Validation failed: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "created", "id": book_id}))
    else:
        typer.echo(f"Created book: {book_id}")


@book_app.command(name="show")
def book_show(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename to show")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show details of a book or all chapters if basename given.

    \b
    If book_id matches an exact entry, shows that book.
    If book_id is a basename (no ch<n> suffix) and chapters exist,
    shows all chapters sequentially.

    \b
    Examples:
        paper-index-tool book show vogelgesang2023ch1    # Single chapter
        paper-index-tool book show vogelgesang2023       # All chapters
        paper-index-tool book show vogelgesang2023 --format json
    """
    logger.info("Showing book: %s", book_id)
    result = _get_book_or_chapters_or_exit(book_id)

    if isinstance(result, list):
        # Multiple chapters found
        logger.info("Found %d chapters for basename '%s'", len(result), book_id)
        _print_chapters_sequential(result, output_format)
    else:
        # Single book
        _print_book_detail(result, output_format)


@book_app.command(name="update")
def book_update(
    book_id: Annotated[str, typer.Argument(help="Book ID to update")],
    # Bibtex fields
    author: Annotated[str | None, typer.Option("--author", help="Author(s)")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Book title")] = None,
    year: Annotated[int | None, typer.Option("--year", help="Publication year")] = None,
    pages: Annotated[str | None, typer.Option("--pages", help="Page range")] = None,
    publisher: Annotated[str | None, typer.Option("--publisher", help="Publisher")] = None,
    url: Annotated[str | None, typer.Option("--url", help="URL")] = None,
    isbn: Annotated[str | None, typer.Option("--isbn", help="ISBN")] = None,
    chapter: Annotated[str | None, typer.Option("--chapter", help="Chapter title/number")] = None,
    file_path_pdf: Annotated[
        str | None, typer.Option("--file-path-pdf", help="Path to PDF")
    ] = None,
    file_path_markdown: Annotated[
        str | None, typer.Option("--file-path-md", help="Path to markdown")
    ] = None,
    keywords: Annotated[
        str | None, typer.Option("--keywords", help="Comma-separated keywords")
    ] = None,
    # Content fields
    abstract: Annotated[str | None, typer.Option("--abstract", help="Book abstract")] = None,
    question: Annotated[str | None, typer.Option("--question", help="Main question/thesis")] = None,
    method: Annotated[str | None, typer.Option("--method", help="Methodology/approach")] = None,
    gaps: Annotated[str | None, typer.Option("--gaps", help="Identified gaps")] = None,
    results: Annotated[str | None, typer.Option("--results", help="Key results")] = None,
    interpretation: Annotated[
        str | None, typer.Option("--interpretation", help="Interpretation")
    ] = None,
    claims: Annotated[str | None, typer.Option("--claims", help="Key claims")] = None,
    full_text: Annotated[
        str | None, typer.Option("--full-text", help="Full book/chapter content")
    ] = None,
    quotes_json: Annotated[
        str | None, typer.Option("--quotes", help="Quotes as JSON array")
    ] = None,
    # Output
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Update an existing book.

    \b
    Only provided fields will be updated. Other fields remain unchanged.

    \b
    Examples:
        paper-index-tool book update vogelgesang2023 --chapter "Updated Chapter"
        paper-index-tool book update vogelgesang2023 --method "Updated method..."
    """
    logger.info("Updating book: %s", book_id)

    registry = BookRegistry()

    # Build updates dict (only non-None values)
    updates: dict[str, object] = {}
    if author is not None:
        updates["author"] = author
    if title is not None:
        updates["title"] = title
    if year is not None:
        updates["year"] = year
    if pages is not None:
        updates["pages"] = pages
    if publisher is not None:
        updates["publisher"] = publisher
    if url is not None:
        updates["url"] = url
    if isbn is not None:
        updates["isbn"] = isbn
    if chapter is not None:
        updates["chapter"] = chapter
    if file_path_pdf is not None:
        updates["file_path_pdf"] = file_path_pdf
    if file_path_markdown is not None:
        updates["file_path_markdown"] = file_path_markdown
    if keywords is not None:
        updates["keywords"] = keywords
    if abstract is not None:
        updates["abstract"] = abstract
    if question is not None:
        updates["question"] = question
    if method is not None:
        updates["method"] = method
    if gaps is not None:
        updates["gaps"] = gaps
    if results is not None:
        updates["results"] = results
    if interpretation is not None:
        updates["interpretation"] = interpretation
    if claims is not None:
        updates["claims"] = claims
    if full_text is not None:
        updates["full_text"] = full_text
    if quotes_json is not None:
        try:
            quotes_data = json.loads(quotes_json)
            updates["quotes"] = [Quote(**q).model_dump() for q in quotes_data]
        except (json.JSONDecodeError, TypeError) as e:
            typer.echo(
                f"Error: Invalid quotes JSON: {e}. "
                f'Expected format: [{{"text": "quote text", "page": 1}}]',
                err=True,
            )
            raise typer.Exit(1)

    if not updates:
        typer.echo(
            "No updates provided. Use --help to see available options.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        registry.update_book(book_id, updates)
    except EntryNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: Validation failed: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "updated", "id": book_id}))
    else:
        typer.echo(f"Updated book: {book_id}")


@book_app.command(name="delete")
def book_delete(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Delete a book or all chapters if basename given.

    \b
    If book_id matches an exact entry, deletes that book.
    If book_id is a basename (no ch<n> suffix) and chapters exist,
    deletes all chapters with one confirmation.

    \b
    Examples:
        paper-index-tool book delete vogelgesang2023ch1    # Single chapter
        paper-index-tool book delete vogelgesang2023       # All chapters
        paper-index-tool book delete vogelgesang2023 --force
    """
    logger.info("Deleting book: %s", book_id)

    registry = BookRegistry()

    # Check if exact match exists
    if registry.book_exists(book_id):
        # Single book delete
        if not force:
            confirm = typer.confirm(f"Delete book '{book_id}'?")
            if not confirm:
                typer.echo("Cancelled")
                raise typer.Exit(0)

        try:
            registry.delete_book(book_id)
        except EntryNotFoundError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"status": "deleted", "id": book_id}))
        else:
            typer.echo(f"Deleted book: {book_id}")
        return

    # Check if basename with chapters
    if not registry.is_chapter_id(book_id):
        chapters = registry.find_chapters(book_id)
        if chapters:
            chapter_ids = [c.id for c in chapters]
            if not force:
                typer.echo(f"Found {len(chapters)} chapters for '{book_id}':")
                for cid in chapter_ids:
                    typer.echo(f"  - {cid}")
                confirm = typer.confirm(f"Delete all {len(chapters)} chapters?")
                if not confirm:
                    typer.echo("Cancelled")
                    raise typer.Exit(0)

            try:
                count = registry.delete_chapters(book_id)
            except EntryNotFoundError as e:
                typer.echo(f"Error: {e}", err=True)
                raise typer.Exit(1)

            if output_format == OutputFormat.JSON:
                typer.echo(
                    json.dumps(
                        {
                            "status": "deleted",
                            "basename": book_id,
                            "count": count,
                            "ids": chapter_ids,
                        }
                    )
                )
            else:
                typer.echo(f"Deleted {count} chapters for '{book_id}'")
            return

    # Not found
    typer.echo(
        f"Error: Book '{book_id}' not found. "
        f"Use 'paper-index-tool book list' to see available books.",
        err=True,
    )
    raise typer.Exit(1)


@book_app.command(name="list")
def book_list(
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
    count: Annotated[
        bool, typer.Option("--count", "-c", help="Show only the count of books")
    ] = False,
) -> None:
    """List all books.

    \b
    Examples:
        paper-index-tool book list
        paper-index-tool book list --format json
        paper-index-tool book list --count
    """
    logger.info("Listing books")

    registry = BookRegistry()
    books = registry.list_books()

    if count:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"count": len(books)}))
        else:
            typer.echo(len(books))
        return

    if output_format == OutputFormat.JSON:
        books_data = [b.model_dump(mode="json") for b in books]
        typer.echo(json.dumps(books_data, indent=2))
    else:
        if not books:
            typer.echo("No books indexed")
            return

        typer.echo(f"Found {len(books)} book(s):\n")
        for book in books:
            _print_book_summary(book, output_format)
            typer.echo()


@book_app.command(name="clear")
def book_clear(
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help="Confirm clearing all books (required for safety)",
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Clear all books from the index.

    This command removes all book entries and clears the BM25 search index.
    Requires --approve flag for safety.

    \b
    Examples:
        # Preview what would be cleared
        paper-index-tool book list

        # Clear all books (requires --approve)
        paper-index-tool book clear --approve
    """
    if not approve:
        typer.echo(
            "Error: This will permanently delete ALL books. Use --approve flag to confirm.",
            err=True,
        )
        raise typer.Exit(1)

    logger.info("Clearing all books")

    registry = BookRegistry()
    count = registry.clear()

    # Clear the BM25 index for books
    from paper_index_tool.search import BookSearcher

    searcher = BookSearcher()
    index_path = searcher.index_path
    if index_path.exists():
        import shutil

        shutil.rmtree(index_path)
        logger.info("Cleared book search index at %s", index_path)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "cleared", "count": count}))
    else:
        typer.echo(f"Cleared {count} book(s) and search index")


# Book field query commands
@book_app.command(name="abstract")
def book_abstract(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show book abstract or all chapter abstracts if basename given.

    \b
    Examples:
        paper-index-tool book abstract vogelgesang2023ch1  # Single chapter
        paper-index-tool book abstract vogelgesang2023     # All chapters
    """
    result = _get_book_or_chapters_or_exit(book_id)
    if isinstance(result, list):
        _print_chapters_field(result, "abstract", output_format)
    else:
        _print_field(book_id, "abstract", result.abstract, output_format)


@book_app.command(name="question")
def book_question(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show main question/thesis or all chapter questions if basename given.

    \b
    Examples:
        paper-index-tool book question vogelgesang2023ch1  # Single chapter
        paper-index-tool book question vogelgesang2023     # All chapters
    """
    result = _get_book_or_chapters_or_exit(book_id)
    if isinstance(result, list):
        _print_chapters_field(result, "question", output_format)
    else:
        _print_field(book_id, "question", result.question, output_format)


@book_app.command(name="method")
def book_method(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show methodology/approach or all chapter methods if basename given.

    \b
    Examples:
        paper-index-tool book method vogelgesang2023ch1  # Single chapter
        paper-index-tool book method vogelgesang2023     # All chapters
    """
    result = _get_book_or_chapters_or_exit(book_id)
    if isinstance(result, list):
        _print_chapters_field(result, "method", output_format)
    else:
        _print_field(book_id, "method", result.method, output_format)


@book_app.command(name="gaps")
def book_gaps(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show identified gaps or all chapter gaps if basename given.

    \b
    Examples:
        paper-index-tool book gaps vogelgesang2023ch1  # Single chapter
        paper-index-tool book gaps vogelgesang2023     # All chapters
    """
    result = _get_book_or_chapters_or_exit(book_id)
    if isinstance(result, list):
        _print_chapters_field(result, "gaps", output_format)
    else:
        _print_field(book_id, "gaps", result.gaps, output_format)


@book_app.command(name="results")
def book_results(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show key results or all chapter results if basename given.

    \b
    Examples:
        paper-index-tool book results vogelgesang2023ch1  # Single chapter
        paper-index-tool book results vogelgesang2023     # All chapters
    """
    result = _get_book_or_chapters_or_exit(book_id)
    if isinstance(result, list):
        _print_chapters_field(result, "results", output_format)
    else:
        _print_field(book_id, "results", result.results, output_format)


@book_app.command(name="claims")
def book_claims(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show key claims or all chapter claims if basename given.

    \b
    Examples:
        paper-index-tool book claims vogelgesang2023ch1  # Single chapter
        paper-index-tool book claims vogelgesang2023     # All chapters
    """
    result = _get_book_or_chapters_or_exit(book_id)
    if isinstance(result, list):
        _print_chapters_field(result, "claims", output_format)
    else:
        _print_field(book_id, "claims", result.claims, output_format)


@book_app.command(name="quotes")
def book_quotes(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show stored quotes with page references or all chapter quotes if basename given.

    \b
    Examples:
        paper-index-tool book quotes vogelgesang2023ch1  # Single chapter
        paper-index-tool book quotes vogelgesang2023     # All chapters
    """
    result = _get_book_or_chapters_or_exit(book_id)

    if isinstance(result, list):
        _print_chapters_field(result, "quotes", output_format)
    else:
        book = result
        if output_format == OutputFormat.JSON:
            quotes_data = [q.model_dump() for q in book.quotes]
            typer.echo(json.dumps({"quotes": quotes_data, "id": book_id}))
        else:
            if not book.quotes:
                typer.echo(f"No quotes stored for book '{book_id}'")
                return

            for i, q in enumerate(book.quotes, 1):
                typer.echo(f'[{i}] "{q.text}" (p. {q.page})')


@book_app.command(name="file-path-pdf")
def book_file_path_pdf(
    book_id: Annotated[str, typer.Argument(help="Book ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show the PDF file path.

    \b
    Examples:
        paper-index-tool book file-path-pdf vogelgesang2023
    """
    book = _get_book_or_exit(book_id)
    _print_field(book_id, "file_path_pdf", book.file_path_pdf, output_format)


@book_app.command(name="file-path-md")
def book_file_path_md(
    book_id: Annotated[str, typer.Argument(help="Book ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show the markdown file path.

    \b
    Examples:
        paper-index-tool book file-path-md vogelgesang2023
    """
    book = _get_book_or_exit(book_id)
    _print_field(book_id, "file_path_markdown", book.file_path_markdown, output_format)


@book_app.command(name="bibtex")
def book_bibtex(
    book_id: Annotated[str, typer.Argument(help="Book ID")],
) -> None:
    """Export book as bibtex entry.

    \b
    Examples:
        paper-index-tool book bibtex vogelgesang2023
    """
    book = _get_book_or_exit(book_id)
    typer.echo(book.to_bibtex())


@book_app.command(name="query")
def book_query(
    book_id: Annotated[str, typer.Argument(help="Book ID or basename to search")],
    search_query: Annotated[str, typer.Argument(help="Search query string")],
    fragments: Annotated[
        bool, typer.Option("--fragments", help="Show matching text fragments")
    ] = False,
    context: Annotated[int, typer.Option("-C", "--context", help="Context lines around match")] = 2,
    num_results: Annotated[int, typer.Option("-n", "--num", help="Number of results")] = 10,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Search within a book or all chapters if basename given.

    \b
    If book_id matches an exact entry, searches that book.
    If book_id is a basename (no ch<n> suffix) and chapters exist,
    searches all chapters and returns union of results with chapter ID prefixes.

    \b
    Examples:
        paper-index-tool book query vogelgesang2023ch1 "leadership"  # Single chapter
        paper-index-tool book query vogelgesang2023 "leadership"     # All chapters
        paper-index-tool book query vogelgesang2023 "identity" --fragments
    """
    import bm25s  # type: ignore[import-untyped]
    import Stemmer  # type: ignore[import-not-found]

    from paper_index_tool.search import extract_fragments

    logger.info("Query: %s in book: %s", search_query, book_id)

    result = _get_book_or_chapters_or_exit(book_id)

    # If single book, delegate to query_command
    if isinstance(result, Book):
        query_command(
            search_query=search_query,
            paper_id=None,
            book_id=book_id,
            all_entries=False,
            fragments=fragments,
            context=context,
            num_results=num_results,
            output_format=output_format,
        )
        return

    # Multiple chapters - search each and union results
    chapters = result
    logger.info("Searching %d chapters for basename '%s'", len(chapters), book_id)

    all_results: list[dict[str, Any]] = []
    stemmer = Stemmer.Stemmer("english")
    query_terms = search_query.split()

    for chapter in chapters:
        content = chapter.get_searchable_text()
        if not content:
            continue

        # BM25 scoring for this chapter
        corpus_tokens = bm25s.tokenize([content], stopwords="en", stemmer=stemmer)
        query_tokens = bm25s.tokenize([search_query], stopwords="en", stemmer=stemmer)

        retriever = bm25s.BM25()
        retriever.index(corpus_tokens)
        _results_array, scores_array = retriever.retrieve(query_tokens, k=1)

        score = float(scores_array[0, 0])
        if score <= 0:
            continue

        # Extract fragments if requested
        frags = []
        if fragments:
            frags = extract_fragments(content, query_terms, context, max_fragments=3)

        chapter_result: dict[str, Any] = {
            "id": chapter.id,
            "type": "book",
            "score": score,
            "title": chapter.title or "",
        }
        if fragments and frags:
            chapter_result["fragments"] = frags

        all_results.append(chapter_result)

    # Sort by score descending and limit
    all_results.sort(key=lambda x: x["score"], reverse=True)
    all_results = all_results[:num_results]

    # Output
    if not all_results:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps([]))
        else:
            typer.echo("No results found")
        return

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps(all_results, indent=2))
    else:
        for r in all_results:
            typer.echo(f"[{r['id']}] score={r['score']:.3f} - {r['title']}")
            if fragments and "fragments" in r:
                for frag in r["fragments"]:
                    typer.echo(f"  Lines {frag['line_start']}-{frag['line_end']}:")
                    typer.echo(f"    {frag['text'][:200]}...")
                typer.echo("")


# =============================================================================
# MEDIA Commands
# =============================================================================


@media_app.command(name="create")
def media_create(
    media_id: Annotated[str, typer.Argument(help="Unique media ID (e.g., ashford2017)")],
    # Core required fields
    media_type: Annotated[
        MediaType, typer.Option("--type", help="Media type: video, podcast, blog")
    ],
    author: Annotated[str, typer.Option("--author", help="Creator/speaker name(s)")],
    title: Annotated[str, typer.Option("--title", help="Title of video/episode/post")],
    year: Annotated[int, typer.Option("--year", help="Publication year")],
    url: Annotated[str, typer.Option("--url", help="Primary URL (required)")],
    access_date: Annotated[str, typer.Option("--access-date", help="Date accessed (YYYY-MM-DD)")],
    file_path_markdown: Annotated[
        str, typer.Option("--file-path-md", help="Path to transcript/content markdown")
    ],
    # Content fields
    abstract: Annotated[str, typer.Option("--abstract", help="Summary")],
    question: Annotated[str, typer.Option("--question", help="Main topic/question addressed")],
    method: Annotated[str, typer.Option("--method", help="Approach/structure")],
    gaps: Annotated[str, typer.Option("--gaps", help="Limitations")],
    results: Annotated[str, typer.Option("--results", help="Key points/findings")],
    interpretation: Annotated[str, typer.Option("--interpretation", help="Analysis/implications")],
    claims: Annotated[str, typer.Option("--claims", help="Verifiable claims")],
    full_text: Annotated[str, typer.Option("--full-text", help="Full transcript/content")],
    # Optional metadata
    keywords: Annotated[str, typer.Option("--keywords", help="Comma-separated keywords")] = "",
    rating: Annotated[int, typer.Option("--rating", min=1, max=5, help="Quality rating 1-5")] = 3,
    # Video-specific optional fields
    platform: Annotated[
        str, typer.Option("--platform", help="Platform name (YouTube, Vimeo, etc.)")
    ] = "",
    channel: Annotated[str, typer.Option("--channel", help="Channel/creator name")] = "",
    duration: Annotated[str, typer.Option("--duration", help="Duration (HH:MM:SS or MM:SS)")] = "",
    video_id: Annotated[str, typer.Option("--video-id", help="Platform-specific video ID")] = "",
    # Podcast-specific optional fields
    show_name: Annotated[str, typer.Option("--show-name", help="Podcast show/series name")] = "",
    episode: Annotated[str, typer.Option("--episode", help="Episode number/identifier")] = "",
    season: Annotated[str, typer.Option("--season", help="Season number")] = "",
    host: Annotated[str, typer.Option("--host", help="Host name(s)")] = "",
    guest: Annotated[str, typer.Option("--guest", help="Guest name(s)")] = "",
    # Blog-specific optional fields
    website: Annotated[str, typer.Option("--website", help="Website/publication name")] = "",
    last_updated: Annotated[
        str | None, typer.Option("--last-updated", help="Last update date (YYYY-MM-DD)")
    ] = None,
    # Optional file paths
    file_path_pdf: Annotated[
        str, typer.Option("--file-path-pdf", help="Path to PDF (if available)")
    ] = "",
    file_path_media: Annotated[
        str, typer.Option("--file-path-media", help="Path to downloaded media file")
    ] = "",
    # AI tracking
    ai_generated: Annotated[
        bool, typer.Option("--ai-generated", help="Whether content was AI-generated")
    ] = False,
    ai_provider: Annotated[
        str | None, typer.Option("--ai-provider", help="AI provider name")
    ] = None,
    ai_model: Annotated[str | None, typer.Option("--ai-model", help="AI model identifier")] = None,
    # Optional quotes
    quotes_json: Annotated[
        str | None, typer.Option("--quotes", help="Quotes as JSON array")
    ] = None,
    # Output
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Create a new media entry (video, podcast, or blog).

    \b
    Required fields vary by type. Core fields always required:
    --type, --author, --title, --year, --url, --access-date, --file-path-md

    \b
    Examples:
        # Create a YouTube video entry
        paper-index-tool media create ashford2017 \\
            --type video --author "TEDx Talks" \\
            --title "Why Everyone Should See Themselves as a Leader" \\
            --year 2017 --url "https://youtube.com/watch?v=..." \\
            --access-date "2025-01-21" --platform "YouTube" \\
            --channel "TEDx Talks" --duration "15:42" \\
            --file-path-md "/path/to/transcript.md" \\
            --abstract "..." --question "..." --method "..." \\
            --gaps "..." --results "..." --interpretation "..." \\
            --claims "..." --full-text "..."

        # Create a podcast entry
        paper-index-tool media create hbr2017 \\
            --type podcast --author "HBR IdeaCast" \\
            --title "Leadership Lessons" --year 2017 \\
            --url "https://hbr.org/podcast/..." \\
            --access-date "2025-01-21" --show-name "HBR IdeaCast" \\
            --episode "42" --host "Sarah Green" \\
            --file-path-md "/path/to/transcript.md" ...
    """
    logger.info("Creating media: %s", media_id)

    registry = MediaRegistry()

    # Check if exists
    if registry.media_exists(media_id):
        typer.echo(
            f"Error: Media '{media_id}' already exists. "
            f"Use 'paper-index-tool media update {media_id}' to modify or "
            f"'paper-index-tool media delete {media_id}' to remove first.",
            err=True,
        )
        raise typer.Exit(1)

    # Parse quotes
    quotes: list[Quote] = []
    if quotes_json:
        try:
            quotes_data = json.loads(quotes_json)
            quotes = [Quote(**q) for q in quotes_data]
        except (json.JSONDecodeError, TypeError) as e:
            typer.echo(
                f"Error: Invalid quotes JSON: {e}. "
                f'Expected format: [{{"text": "quote text", "timestamp": "05:30"}}]',
                err=True,
            )
            raise typer.Exit(1)

    # Create media
    try:
        media = Media(
            id=media_id,
            media_type=media_type,
            author=author,
            title=title,
            year=year,
            url=url,
            access_date=access_date,
            keywords=keywords,
            rating=rating,
            platform=platform,
            channel=channel,
            duration=duration,
            video_id=video_id,
            show_name=show_name,
            episode=episode,
            season=season,
            host=host,
            guest=guest,
            website=website,
            last_updated=last_updated,
            file_path_markdown=file_path_markdown,
            file_path_pdf=file_path_pdf,
            file_path_media=file_path_media,
            abstract=abstract,
            question=question,
            method=method,
            gaps=gaps,
            results=results,
            interpretation=interpretation,
            claims=claims,
            quotes=quotes,
            full_text=full_text,
            ai_generated=ai_generated,
            ai_provider=ai_provider,
            ai_model=ai_model,
        )
        registry.add_media(media)
    except EntryExistsError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: Validation failed: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "created", "id": media_id, "type": media_type.value}))
    else:
        typer.echo(f"Created media ({media_type.value}): {media_id}")


@media_app.command(name="show")
def media_show(
    media_id: Annotated[str, typer.Argument(help="Media ID to show")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show details of a media entry.

    \b
    Examples:
        paper-index-tool media show ashford2017
        paper-index-tool media show ashford2017 --format json
    """
    logger.info("Showing media: %s", media_id)
    media = _get_media_or_exit(media_id)
    _print_media_detail(media, output_format)


@media_app.command(name="update")
def media_update(
    media_id: Annotated[str, typer.Argument(help="Media ID to update")],
    # Core fields
    media_type: Annotated[MediaType | None, typer.Option("--type", help="Media type")] = None,
    author: Annotated[str | None, typer.Option("--author", help="Creator/speaker name(s)")] = None,
    title: Annotated[str | None, typer.Option("--title", help="Title")] = None,
    year: Annotated[int | None, typer.Option("--year", help="Publication year")] = None,
    url: Annotated[str | None, typer.Option("--url", help="Primary URL")] = None,
    access_date: Annotated[str | None, typer.Option("--access-date", help="Date accessed")] = None,
    keywords: Annotated[
        str | None, typer.Option("--keywords", help="Comma-separated keywords")
    ] = None,
    rating: Annotated[
        int | None, typer.Option("--rating", min=1, max=5, help="Quality rating 1-5")
    ] = None,
    # Video-specific fields
    platform: Annotated[str | None, typer.Option("--platform", help="Platform name")] = None,
    channel: Annotated[str | None, typer.Option("--channel", help="Channel/creator name")] = None,
    duration: Annotated[str | None, typer.Option("--duration", help="Duration")] = None,
    video_id: Annotated[
        str | None, typer.Option("--video-id", help="Platform-specific video ID")
    ] = None,
    # Podcast-specific fields
    show_name: Annotated[
        str | None, typer.Option("--show-name", help="Podcast show/series name")
    ] = None,
    episode: Annotated[
        str | None, typer.Option("--episode", help="Episode number/identifier")
    ] = None,
    season: Annotated[str | None, typer.Option("--season", help="Season number")] = None,
    host: Annotated[str | None, typer.Option("--host", help="Host name(s)")] = None,
    guest: Annotated[str | None, typer.Option("--guest", help="Guest name(s)")] = None,
    # Blog-specific fields
    website: Annotated[
        str | None, typer.Option("--website", help="Website/publication name")
    ] = None,
    last_updated: Annotated[
        str | None, typer.Option("--last-updated", help="Last update date")
    ] = None,
    # File paths
    file_path_markdown: Annotated[
        str | None, typer.Option("--file-path-md", help="Path to markdown")
    ] = None,
    file_path_pdf: Annotated[
        str | None, typer.Option("--file-path-pdf", help="Path to PDF")
    ] = None,
    file_path_media: Annotated[
        str | None, typer.Option("--file-path-media", help="Path to media file")
    ] = None,
    # Content fields
    abstract: Annotated[str | None, typer.Option("--abstract", help="Summary")] = None,
    question: Annotated[str | None, typer.Option("--question", help="Main topic/question")] = None,
    method: Annotated[str | None, typer.Option("--method", help="Approach/structure")] = None,
    gaps: Annotated[str | None, typer.Option("--gaps", help="Limitations")] = None,
    results: Annotated[str | None, typer.Option("--results", help="Key points/findings")] = None,
    interpretation: Annotated[
        str | None, typer.Option("--interpretation", help="Analysis/implications")
    ] = None,
    claims: Annotated[str | None, typer.Option("--claims", help="Verifiable claims")] = None,
    full_text: Annotated[
        str | None, typer.Option("--full-text", help="Full transcript/content")
    ] = None,
    quotes_json: Annotated[
        str | None, typer.Option("--quotes", help="Quotes as JSON array")
    ] = None,
    # AI tracking
    ai_generated: Annotated[
        bool | None, typer.Option("--ai-generated", help="AI-generated flag")
    ] = None,
    ai_provider: Annotated[
        str | None, typer.Option("--ai-provider", help="AI provider name")
    ] = None,
    ai_model: Annotated[str | None, typer.Option("--ai-model", help="AI model identifier")] = None,
    # Output
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Update an existing media entry.

    \b
    Only provided fields will be updated. Other fields remain unchanged.

    \b
    Examples:
        paper-index-tool media update ashford2017 --rating 5
        paper-index-tool media update ashford2017 --duration "16:30"
    """
    logger.info("Updating media: %s", media_id)

    registry = MediaRegistry()

    # Build updates dict (only non-None values)
    updates: dict[str, object] = {}
    if media_type is not None:
        updates["media_type"] = media_type.value
    if author is not None:
        updates["author"] = author
    if title is not None:
        updates["title"] = title
    if year is not None:
        updates["year"] = year
    if url is not None:
        updates["url"] = url
    if access_date is not None:
        updates["access_date"] = access_date
    if keywords is not None:
        updates["keywords"] = keywords
    if rating is not None:
        updates["rating"] = rating
    if platform is not None:
        updates["platform"] = platform
    if channel is not None:
        updates["channel"] = channel
    if duration is not None:
        updates["duration"] = duration
    if video_id is not None:
        updates["video_id"] = video_id
    if show_name is not None:
        updates["show_name"] = show_name
    if episode is not None:
        updates["episode"] = episode
    if season is not None:
        updates["season"] = season
    if host is not None:
        updates["host"] = host
    if guest is not None:
        updates["guest"] = guest
    if website is not None:
        updates["website"] = website
    if last_updated is not None:
        updates["last_updated"] = last_updated
    if file_path_markdown is not None:
        updates["file_path_markdown"] = file_path_markdown
    if file_path_pdf is not None:
        updates["file_path_pdf"] = file_path_pdf
    if file_path_media is not None:
        updates["file_path_media"] = file_path_media
    if abstract is not None:
        updates["abstract"] = abstract
    if question is not None:
        updates["question"] = question
    if method is not None:
        updates["method"] = method
    if gaps is not None:
        updates["gaps"] = gaps
    if results is not None:
        updates["results"] = results
    if interpretation is not None:
        updates["interpretation"] = interpretation
    if claims is not None:
        updates["claims"] = claims
    if full_text is not None:
        updates["full_text"] = full_text
    if ai_generated is not None:
        updates["ai_generated"] = ai_generated
    if ai_provider is not None:
        updates["ai_provider"] = ai_provider
    if ai_model is not None:
        updates["ai_model"] = ai_model
    if quotes_json is not None:
        try:
            quotes_data = json.loads(quotes_json)
            updates["quotes"] = [Quote(**q).model_dump() for q in quotes_data]
        except (json.JSONDecodeError, TypeError) as e:
            typer.echo(
                f"Error: Invalid quotes JSON: {e}. "
                f'Expected format: [{{"text": "quote text", "timestamp": "05:30"}}]',
                err=True,
            )
            raise typer.Exit(1)

    if not updates:
        typer.echo(
            "No updates provided. Use --help to see available options.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        registry.update_media(media_id, updates)
    except EntryNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: Validation failed: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "updated", "id": media_id}))
    else:
        typer.echo(f"Updated media: {media_id}")


@media_app.command(name="delete")
def media_delete(
    media_id: Annotated[str, typer.Argument(help="Media ID to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Delete a media entry.

    \b
    Examples:
        paper-index-tool media delete ashford2017
        paper-index-tool media delete ashford2017 --force
    """
    logger.info("Deleting media: %s", media_id)

    registry = MediaRegistry()

    if not registry.media_exists(media_id):
        typer.echo(
            f"Error: Media '{media_id}' not found. "
            f"Use 'paper-index-tool media list' to see available media.",
            err=True,
        )
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete media '{media_id}'?")
        if not confirm:
            typer.echo("Cancelled")
            raise typer.Exit(0)

    try:
        registry.delete_media(media_id)
    except EntryNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "deleted", "id": media_id}))
    else:
        typer.echo(f"Deleted media: {media_id}")


@media_app.command(name="list")
def media_list(
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
    count: Annotated[
        bool, typer.Option("--count", "-c", help="Show only the count of media entries")
    ] = False,
    media_type_filter: Annotated[
        MediaType | None, typer.Option("--type", "-t", help="Filter by media type")
    ] = None,
) -> None:
    """List all media entries.

    \b
    Examples:
        paper-index-tool media list
        paper-index-tool media list --format json
        paper-index-tool media list --count
        paper-index-tool media list --type video
        paper-index-tool media list --type podcast
    """
    logger.info("Listing media")

    registry = MediaRegistry()
    all_media = registry.list_media()

    # Apply type filter if specified
    if media_type_filter:
        all_media = [m for m in all_media if m.media_type == media_type_filter]

    if count:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps({"count": len(all_media)}))
        else:
            typer.echo(len(all_media))
        return

    if output_format == OutputFormat.JSON:
        media_data = [m.model_dump(mode="json") for m in all_media]
        typer.echo(json.dumps(media_data, indent=2))
    else:
        if not all_media:
            typer.echo("No media indexed")
            return

        type_msg = f" ({media_type_filter.value})" if media_type_filter else ""
        typer.echo(f"Found {len(all_media)} media{type_msg}:\n")
        for media in all_media:
            _print_media_summary(media, output_format)
            typer.echo()


@media_app.command(name="clear")
def media_clear(
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help="Confirm clearing all media (required for safety)",
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Clear all media from the index.

    This command removes all media entries. Requires --approve flag for safety.

    \b
    Examples:
        # Preview what would be cleared
        paper-index-tool media list

        # Clear all media (requires --approve)
        paper-index-tool media clear --approve
    """
    if not approve:
        typer.echo(
            "Error: This will permanently delete ALL media. Use --approve flag to confirm.",
            err=True,
        )
        raise typer.Exit(1)

    logger.info("Clearing all media")

    registry = MediaRegistry()
    count = registry.clear()

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "cleared", "count": count}))
    else:
        typer.echo(f"Cleared {count} media entry(ies)")


# Media field query commands
@media_app.command(name="abstract")
def media_abstract(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show media summary/abstract.

    \b
    Examples:
        paper-index-tool media abstract ashford2017
    """
    media = _get_media_or_exit(media_id)
    _print_field(media_id, "abstract", media.abstract, output_format)


@media_app.command(name="question")
def media_question(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show main topic/question.

    \b
    Examples:
        paper-index-tool media question ashford2017
    """
    media = _get_media_or_exit(media_id)
    _print_field(media_id, "question", media.question, output_format)


@media_app.command(name="method")
def media_method(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show approach/structure.

    \b
    Examples:
        paper-index-tool media method ashford2017
    """
    media = _get_media_or_exit(media_id)
    _print_field(media_id, "method", media.method, output_format)


@media_app.command(name="gaps")
def media_gaps(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show limitations.

    \b
    Examples:
        paper-index-tool media gaps ashford2017
    """
    media = _get_media_or_exit(media_id)
    _print_field(media_id, "gaps", media.gaps, output_format)


@media_app.command(name="results")
def media_results(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show key points/findings.

    \b
    Examples:
        paper-index-tool media results ashford2017
    """
    media = _get_media_or_exit(media_id)
    _print_field(media_id, "results", media.results, output_format)


@media_app.command(name="claims")
def media_claims(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show verifiable claims.

    \b
    Examples:
        paper-index-tool media claims ashford2017
    """
    media = _get_media_or_exit(media_id)
    _print_field(media_id, "claims", media.claims, output_format)


@media_app.command(name="quotes")
def media_quotes(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show stored quotes with timestamps.

    \b
    Examples:
        paper-index-tool media quotes ashford2017
    """
    media = _get_media_or_exit(media_id)

    if output_format == OutputFormat.JSON:
        quotes_data = [q.model_dump() for q in media.quotes]
        typer.echo(json.dumps({"quotes": quotes_data, "id": media_id}))
    else:
        if not media.quotes:
            typer.echo(f"No quotes stored for media '{media_id}'")
            return

        for i, q in enumerate(media.quotes, 1):
            if q.timestamp:
                typer.echo(f'[{i}] "{q.text}" ({q.timestamp})')
            elif q.page:
                typer.echo(f'[{i}] "{q.text}" (p. {q.page})')
            else:
                typer.echo(f'[{i}] "{q.text}"')


@media_app.command(name="transcript")
def media_transcript(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show full transcript/content (alias for full_text).

    \b
    Examples:
        paper-index-tool media transcript ashford2017
    """
    media = _get_media_or_exit(media_id)
    _print_field(media_id, "full_text", media.full_text, output_format)


@media_app.command(name="file-path-md")
def media_file_path_md(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Show the markdown file path.

    \b
    Examples:
        paper-index-tool media file-path-md ashford2017
    """
    media = _get_media_or_exit(media_id)
    _print_field(media_id, "file_path_markdown", media.file_path_markdown, output_format)


@media_app.command(name="bibtex")
def media_bibtex(
    media_id: Annotated[str, typer.Argument(help="Media ID")],
) -> None:
    """Export media as bibtex entry.

    \b
    Exports as @misc for video/podcast or @online for blog.

    \b
    Examples:
        paper-index-tool media bibtex ashford2017
    """
    media = _get_media_or_exit(media_id)
    typer.echo(media.to_bibtex())


@media_app.command(name="query")
def media_query(
    media_id: Annotated[str, typer.Argument(help="Media ID to search")],
    search_query: Annotated[str, typer.Argument(help="Search query string")],
    fragments: Annotated[
        bool, typer.Option("--fragments", help="Show matching text fragments")
    ] = False,
    context: Annotated[int, typer.Option("-C", "--context", help="Context lines around match")] = 2,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Search within a single media entry using BM25.

    \b
    Examples:
        paper-index-tool media query ashford2017 "leadership identity"
        paper-index-tool media query ashford2017 "narcissism" --fragments
    """
    # Search single media entry
    media = _get_media_or_exit(media_id)
    content = media.get_searchable_text()

    if not content:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps([]))
        else:
            typer.echo("No searchable content in media")
        return

    # Use BM25 for scoring
    import bm25s
    import Stemmer

    from paper_index_tool.search import extract_fragments

    stemmer = Stemmer.Stemmer("english")
    corpus_tokens = bm25s.tokenize([content], stopwords="en", stemmer=stemmer)
    query_tokens = bm25s.tokenize([search_query], stopwords="en", stemmer=stemmer)

    retriever = bm25s.BM25()
    retriever.index(corpus_tokens)
    _results_array, scores_array = retriever.retrieve(query_tokens, k=1)

    score = float(scores_array[0, 0])
    if score <= 0:
        if output_format == OutputFormat.JSON:
            typer.echo(json.dumps([]))
        else:
            typer.echo("No results found")
        return

    # Extract fragments if requested
    query_terms = search_query.split()
    frags = []
    if fragments:
        frags = extract_fragments(content, query_terms, context, max_fragments=3)

    if output_format == OutputFormat.JSON:
        media_result: dict[str, Any] = {
            "id": media_id,
            "type": "media",
            "media_type": media.media_type.value,
            "score": score,
            "title": media.title,
        }
        if fragments:
            media_result["fragments"] = frags
        typer.echo(json.dumps([media_result], indent=2))
    else:
        typer.echo(f"[1] {media_id} (score: {score:.4f})")
        typer.echo(f"    Title: {media.title}")
        typer.echo(f"    Type: {media.media_type.value}")

        if fragments and frags:
            for j, frag in enumerate(frags, 1):
                line_range = f"{frag['line_start']}-{frag['line_end']}"
                typer.echo(f"\n    Fragment {j} (lines {line_range}):")
                typer.echo("    " + "-" * 40)
                for line in frag["lines"]:
                    typer.echo(f"    {line}")


# =============================================================================
# Stats Command
# =============================================================================


@app.command(name="stats")
def stats_command(
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format: human or json")
    ] = OutputFormat.HUMAN,
) -> None:
    """Display statistics for all indexed entries.

    \b
    STATISTICS SHOWN:
        - Total count (papers + books + media)
        - Media breakdown by type (video, podcast, blog)
        - Top 10 authors by entry count
        - Entries by publication year
        - Top 10 keywords by frequency

    \b
    EXAMPLES:
        # Human-readable table format
        paper-index-tool stats

        # JSON for programmatic access
        paper-index-tool stats --format json

    \b
    JSON OUTPUT SCHEMA:
        {
          "total_count": 25,
          "paper_count": 15,
          "book_count": 5,
          "media_count": 5,
          "media_by_type": {"video": 3, "podcast": 2},
          "authors_top_10": {"Ashford, S. J.": 3, ...},
          "years": {"2023": 5, "2022": 8, ...},
          "keywords_top_10": {"leadership": 10, ...}
        }
    """
    logger.info("Generating statistics")

    paper_registry = PaperRegistry()
    book_registry = BookRegistry()
    media_registry = MediaRegistry()

    papers = paper_registry.list_papers()
    books = book_registry.list_books()
    media_list = media_registry.list_media()

    # Collect stats
    paper_count = len(papers)
    book_count = len(books)
    media_count = len(media_list)
    total_count = paper_count + book_count + media_count

    # Media type breakdown
    media_types: Counter[str] = Counter()
    for media in media_list:
        media_types[media.media_type.value] += 1

    # Author breakdown
    authors: Counter[str] = Counter()
    for paper in papers:
        if paper.author:
            # Take first author for counting
            first_author = paper.author.split(" and ")[0].strip()
            authors[first_author] += 1
    for book in books:
        if book.author:
            first_author = book.author.split(" and ")[0].strip()
            authors[first_author] += 1
    for media in media_list:
        if media.author:
            first_author = media.author.split(" and ")[0].strip()
            authors[first_author] += 1

    # Year breakdown
    years: Counter[int] = Counter()
    for paper in papers:
        if paper.year:
            years[paper.year] += 1
    for book in books:
        if book.year:
            years[book.year] += 1
    for media in media_list:
        if media.year:
            years[media.year] += 1

    # Keywords breakdown
    keywords_counter: Counter[str] = Counter()
    for paper in papers:
        if paper.keywords:
            for kw in paper.keywords.split(","):
                keywords_counter[kw.strip().lower()] += 1
    for book in books:
        if book.keywords:
            for kw in book.keywords.split(","):
                keywords_counter[kw.strip().lower()] += 1
    for media in media_list:
        if media.keywords:
            for kw in media.keywords.split(","):
                keywords_counter[kw.strip().lower()] += 1

    if output_format == OutputFormat.JSON:
        stats_data = {
            "total_count": total_count,
            "paper_count": paper_count,
            "book_count": book_count,
            "media_count": media_count,
            "media_by_type": dict(media_types),
            "authors_top_10": dict(authors.most_common(10)),
            "years": dict(sorted(years.items())),
            "keywords_top_10": dict(keywords_counter.most_common(10)),
        }
        typer.echo(json.dumps(stats_data, indent=2))
    else:
        # Human readable table format
        typer.echo("=" * 60)
        typer.echo("PAPER INDEX STATISTICS")
        typer.echo("=" * 60)

        typer.echo(f"\nTotal Entries: {total_count}")
        typer.echo(f"  - Papers: {paper_count}")
        typer.echo(f"  - Books:  {book_count}")
        typer.echo(f"  - Media:  {media_count}")
        if media_types:
            for mtype, mcount in sorted(media_types.items()):
                typer.echo(f"      {mtype}: {mcount}")

        if authors:
            typer.echo("\n--- Top 10 Authors ---")
            typer.echo(f"{'Author':<40} {'Count':>5}")
            typer.echo("-" * 45)
            for author, count in authors.most_common(10):
                display_author = author[:37] + "..." if len(author) > 40 else author
                typer.echo(f"{display_author:<40} {count:>5}")

        if years:
            typer.echo("\n--- By Year ---")
            typer.echo(f"{'Year':<10} {'Count':>5}")
            typer.echo("-" * 15)
            for year in sorted(years.keys(), reverse=True):
                typer.echo(f"{year:<10} {years[year]:>5}")

        if keywords_counter:
            typer.echo("\n--- Top 10 Keywords ---")
            typer.echo(f"{'Keyword':<30} {'Count':>5}")
            typer.echo("-" * 35)
            for keyword, count in keywords_counter.most_common(10):
                display_kw = keyword[:27] + "..." if len(keyword) > 30 else keyword
                typer.echo(f"{display_kw:<30} {count:>5}")

        typer.echo()


# =============================================================================
# Export Command
# =============================================================================


@app.command(name="export")
def export_command(
    filename: Annotated[str, typer.Argument(help="Output JSON file path (supports ~)")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing file")] = False,
) -> None:
    """Export all papers and books to a JSON backup file.

    \b
    EXPORT FORMAT (JSON):
        {
          "version": "1.0",
          "exported_at": "2024-01-15T10:30:00",
          "paper_count": 15,
          "book_count": 5,
          "papers": [...],
          "books": [...]
        }

    \b
    EXAMPLES:
        # Export to current directory
        paper-index-tool export backup.json

        # Export to home directory (overwrite if exists)
        paper-index-tool export ~/papers-backup.json --force

    \b
    SEE ALSO:
        import   Import data from JSON backup
    """
    logger.info("Exporting to: %s", filename)

    output_path = Path(filename).expanduser()

    if output_path.exists() and not force:
        typer.echo(
            f"Error: File '{output_path}' already exists. Use --force to overwrite.",
            err=True,
        )
        raise typer.Exit(1)

    paper_registry = PaperRegistry()
    book_registry = BookRegistry()

    papers = paper_registry.list_papers()
    books = book_registry.list_books()

    export_data: dict[str, Any] = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "paper_count": len(papers),
        "book_count": len(books),
        "papers": [p.model_dump(mode="json") for p in papers],
        "books": [b.model_dump(mode="json") for b in books],
    }

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=2, default=str)

    typer.echo(f"Exported {len(papers)} papers and {len(books)} books to {output_path}")


# =============================================================================
# Import Command
# =============================================================================


@app.command(name="import")
def import_command(
    filename: Annotated[str, typer.Argument(help="Input JSON file path (supports ~)")],
    replace: Annotated[
        bool,
        typer.Option("--replace", help="Clear all existing data before import (default)"),
    ] = True,
    merge: Annotated[
        bool,
        typer.Option("--merge", help="Add new entries only, skip existing IDs"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview import without making changes"),
    ] = False,
) -> None:
    """Import papers and books from a JSON backup file.

    \b
    IMPORT MODES (mutually exclusive):
        --replace   Clear ALL existing data, then import (default)
        --merge     Add new entries only, skip if ID exists

    \b
    AUTOMATIC ACTIONS:
        - Validates JSON structure before import
        - Rebuilds BM25 search index after import

    \b
    EXAMPLES:
        # Full restore (clears existing data)
        paper-index-tool import backup.json

        # Add new entries without overwriting
        paper-index-tool import new-papers.json --merge

        # Preview what would be imported
        paper-index-tool import backup.json --dry-run

    \b
    SEE ALSO:
        export   Export all data to JSON backup
    """
    logger.info("Importing from: %s", filename)

    input_path = Path(filename).expanduser()

    if not input_path.exists():
        typer.echo(
            f"Error: File '{input_path}' not found. Please provide a valid JSON file path.",
            err=True,
        )
        raise typer.Exit(1)

    # Handle conflicting options
    if merge:
        replace = False

    # Load and validate file
    try:
        with open(input_path) as f:
            import_data = json.load(f)
    except json.JSONDecodeError as e:
        typer.echo(
            f"Error: Invalid JSON in file '{input_path}': {e}. Please check the file format.",
            err=True,
        )
        raise typer.Exit(1)

    # Extract papers and books
    papers_data = import_data.get("papers", [])
    books_data = import_data.get("books", [])

    if dry_run:
        typer.echo("DRY RUN - No changes will be made\n")
        typer.echo(f"Would import {len(papers_data)} papers and {len(books_data)} books")
        typer.echo(f"Mode: {'replace' if replace else 'merge'}")

        if papers_data:
            typer.echo("\nPapers to import:")
            for p in papers_data[:10]:  # Show first 10
                typer.echo(f"  - {p.get('id', 'unknown')}: {p.get('title', 'No title')[:50]}")
            if len(papers_data) > 10:
                typer.echo(f"  ... and {len(papers_data) - 10} more")

        if books_data:
            typer.echo("\nBooks to import:")
            for b in books_data[:10]:  # Show first 10
                typer.echo(f"  - {b.get('id', 'unknown')}: {b.get('title', 'No title')[:50]}")
            if len(books_data) > 10:
                typer.echo(f"  ... and {len(books_data) - 10} more")

        return

    paper_registry = PaperRegistry()
    book_registry = BookRegistry()

    # Convert to dict format for import_all
    papers_dict = {p["id"]: p for p in papers_data if "id" in p}
    books_dict = {b["id"]: b for b in books_data if "id" in b}

    # Import
    try:
        paper_count = paper_registry.import_all(papers_dict, replace=replace)
        book_count = book_registry.import_all(books_dict, replace=replace)
    except ValueError as e:
        typer.echo(f"Error: Import validation failed: {e}", err=True)
        raise typer.Exit(1)

    # Rebuild BM25 index
    from paper_index_tool.search import PaperSearcher

    searcher = PaperSearcher()
    index_count = searcher.rebuild_index()

    mode_str = "Replaced" if replace else "Merged"
    typer.echo(f"{mode_str} {paper_count} papers and {book_count} books")
    typer.echo(f"Rebuilt BM25 index with {index_count} entries")


# =============================================================================
# Create from JSON Command
# =============================================================================


def _detect_entry_type(data: dict[str, Any]) -> str:
    """Detect if JSON data represents a paper or book.

    Papers have 'journal' field, books have 'chapter' or 'chapter_title' field.

    Args:
        data: JSON data dictionary.

    Returns:
        'paper' or 'book' string.
    """
    if "journal" in data:
        return "paper"
    if "chapter" in data or "chapter_title" in data or "chapter_number" in data:
        return "book"
    # Default to paper if ambiguous
    return "paper"


def _transform_book_data(data: dict[str, Any]) -> dict[str, Any]:
    """Transform book JSON data to match the Book model fields.

    Handles alternate field names from JSON generation:
    - book_title -> title
    - chapter_title + chapter_number -> chapter
    - key_concepts + summary -> question, method, gaps, results, interpretation, claims

    Args:
        data: Raw JSON data dictionary.

    Returns:
        Transformed data dictionary matching Book model fields.
    """
    transformed = data.copy()

    # Map book_title to title
    if "book_title" in transformed and "title" not in transformed:
        transformed["title"] = transformed.pop("book_title")

    # Combine chapter_title and chapter_number into chapter
    if "chapter" not in transformed:
        chapter_parts = []
        if "chapter_number" in transformed:
            chapter_parts.append(f"Chapter {transformed.pop('chapter_number')}")
        if "chapter_title" in transformed:
            chapter_parts.append(transformed.pop("chapter_title"))
        if chapter_parts:
            transformed["chapter"] = (
                " - ".join(chapter_parts) if len(chapter_parts) > 1 else chapter_parts[0]
            )

    # Map key_concepts and summary to content fields if missing
    key_concepts = transformed.pop("key_concepts", "")
    summary = transformed.pop("summary", "")

    # Use key_concepts for claims if not present
    if "claims" not in transformed and key_concepts:
        transformed["claims"] = key_concepts

    # Use summary for other content fields if not present
    for field in ["question", "method", "gaps", "results", "interpretation"]:
        if field not in transformed:
            transformed[field] = summary if summary else "See full text"

    return transformed


def _populate_full_text_from_markdown(data: dict[str, Any]) -> dict[str, Any]:
    """Auto-populate full_text field by reading from file_path_markdown.

    If file_path_markdown is provided and full_text is missing or empty,
    reads the entire markdown file content into full_text for BM25 indexing.

    Args:
        data: JSON data dictionary with entry fields.

    Returns:
        Modified data dict with full_text populated from markdown file.
    """
    markdown_path = data.get("file_path_markdown")
    full_text = data.get("full_text")

    # Only populate if markdown path exists and full_text is missing/empty
    if markdown_path and (not full_text or not full_text.strip()):
        expanded_path = Path(markdown_path).expanduser()
        if expanded_path.exists():
            try:
                with open(expanded_path, encoding="utf-8") as f:
                    data["full_text"] = f.read()
                logger.info(
                    "Auto-populated full_text from %s (%d chars)",
                    markdown_path,
                    len(data["full_text"]),
                )
            except OSError as e:
                logger.warning("Could not read markdown file %s: %s", markdown_path, e)
        else:
            logger.warning("Markdown file not found: %s", markdown_path)

    return data


@app.command(name="create-from-json")
def create_from_json(
    filename: Annotated[str, typer.Argument(help="Path to JSON file with entry data")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format: human or json")
    ] = OutputFormat.HUMAN,
) -> None:
    """Create a paper or book entry from a JSON file.

    \b
    AUTO-DETECTION:
        - 'journal' field present → creates paper
        - 'chapter' field present → creates book

    \b
    AUTO-POPULATION:
        - If 'file_path_markdown' provided and 'full_text' empty,
          full_text is automatically read from the markdown file

    \b
    REQUIRED JSON FIELDS:
        - id: Unique identifier (format: authorname2024)
        - author, title, year: Basic metadata
        - (paper) journal, volume, number, issue, pages, publisher, doi
        - (book) chapter, pages, publisher
        - abstract, question, method, gaps, results, interpretation, claims

    \b
    EXAMPLES:
        # Create paper from JSON
        paper-index-tool create-from-json ashford2012.json

        # Create book from JSON
        paper-index-tool create-from-json vogelgesang2023.json

        # JSON output for scripting
        paper-index-tool create-from-json paper.json --format json

    \b
    SEE ALSO:
        update-from-json   Update existing entry from JSON
        export             Export all entries to JSON backup
    """
    logger.info("Creating from JSON: %s", filename)

    input_path = Path(filename).expanduser()

    if not input_path.exists():
        typer.echo(
            f"Error: File '{input_path}' not found. Please provide a valid JSON file path.",
            err=True,
        )
        raise typer.Exit(1)

    # Load JSON
    try:
        with open(input_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        typer.echo(
            f"Error: Invalid JSON in file '{input_path}': {e}. Please check the file format.",
            err=True,
        )
        raise typer.Exit(1)

    # Auto-populate full_text from file_path_markdown if not provided
    data = _populate_full_text_from_markdown(data)

    if "id" not in data:
        typer.echo(
            "Error: JSON must contain an 'id' field. "
            "Please add an id in format <surname><year>, e.g., 'ashford2012'.",
            err=True,
        )
        raise typer.Exit(1)

    entry_type = _detect_entry_type(data)

    # Transform book data to match expected model fields
    if entry_type == "book":
        data = _transform_book_data(data)

    entry_id = data["id"]

    try:
        if entry_type == "paper":
            paper = Paper.model_validate(data)
            paper_registry = PaperRegistry()
            if paper_registry.paper_exists(entry_id):
                typer.echo(
                    f"Error: Paper '{entry_id}' already exists. "
                    f"Use 'update-from-json' to modify existing entries.",
                    err=True,
                )
                raise typer.Exit(1)
            paper_registry.add_paper(paper)
        else:
            book = Book.model_validate(data)
            book_registry = BookRegistry()
            if book_registry.book_exists(entry_id):
                typer.echo(
                    f"Error: Book '{entry_id}' already exists. "
                    f"Use 'update-from-json' to modify existing entries.",
                    err=True,
                )
                raise typer.Exit(1)
            book_registry.add_book(book)
    except ValueError as e:
        typer.echo(f"Error: Validation failed: {e}", err=True)
        raise typer.Exit(1)
    except EntryExistsError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "created", "type": entry_type, "id": entry_id}))
    else:
        typer.echo(f"Created {entry_type}: {entry_id}")


# =============================================================================
# Update from JSON Command
# =============================================================================


@app.command(name="update-from-json")
def update_from_json(
    filename: Annotated[str, typer.Argument(help="Input JSON file path")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format")
    ] = OutputFormat.HUMAN,
) -> None:
    """Update entry from a JSON file.

    \b
    Auto-detects if the JSON represents a paper or book:
    - If 'journal' field present: updates paper
    - If 'chapter' field present: updates book

    The entry must already exist. All fields in the JSON will be applied.

    \b
    Examples:
        paper-index-tool update-from-json ashford2012.json
        paper-index-tool update-from-json vogelgesang2023.json
    """
    logger.info("Updating from JSON: %s", filename)

    input_path = Path(filename).expanduser()

    if not input_path.exists():
        typer.echo(
            f"Error: File '{input_path}' not found. Please provide a valid JSON file path.",
            err=True,
        )
        raise typer.Exit(1)

    # Load JSON
    try:
        with open(input_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        typer.echo(
            f"Error: Invalid JSON in file '{input_path}': {e}. Please check the file format.",
            err=True,
        )
        raise typer.Exit(1)

    # Auto-populate full_text from file_path_markdown if not provided
    data = _populate_full_text_from_markdown(data)

    if "id" not in data:
        typer.echo(
            "Error: JSON must contain an 'id' field. "
            "Please add an id in format <surname><year>, e.g., 'ashford2012'.",
            err=True,
        )
        raise typer.Exit(1)

    entry_type = _detect_entry_type(data)
    entry_id = data["id"]

    # Remove id from updates
    updates = {k: v for k, v in data.items() if k != "id"}

    try:
        if entry_type == "paper":
            paper_registry = PaperRegistry()
            if not paper_registry.paper_exists(entry_id):
                typer.echo(
                    f"Error: Paper '{entry_id}' not found. "
                    f"Use 'create-from-json' to create new entries.",
                    err=True,
                )
                raise typer.Exit(1)
            paper_registry.update_paper(entry_id, updates)
        else:
            book_registry = BookRegistry()
            if not book_registry.book_exists(entry_id):
                typer.echo(
                    f"Error: Book '{entry_id}' not found. "
                    f"Use 'create-from-json' to create new entries.",
                    err=True,
                )
                raise typer.Exit(1)
            book_registry.update_book(entry_id, updates)
    except EntryNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: Validation failed: {e}", err=True)
        raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        typer.echo(json.dumps({"status": "updated", "type": entry_type, "id": entry_id}))
    else:
        typer.echo(f"Updated {entry_type}: {entry_id}")


# =============================================================================
# Search Commands
# =============================================================================


@app.command(name="query")
def query_command(
    search_query: Annotated[
        str, typer.Argument(help="Search terms (BM25) or natural language (semantic)")
    ],
    paper_id: Annotated[
        str | None, typer.Option("--paper", "-p", help="Search single paper by ID")
    ] = None,
    book_id: Annotated[
        str | None, typer.Option("--book", "-b", help="Search single book by ID")
    ] = None,
    all_entries: Annotated[
        bool, typer.Option("--all", "-a", help="Search all papers, books, and media")
    ] = False,
    semantic: Annotated[
        bool, typer.Option("--semantic", "-s", help="Semantic search (natural language)")
    ] = False,
    fragments: Annotated[
        bool, typer.Option("--fragments", help="Include matching text fragments in output")
    ] = False,
    context: Annotated[
        int, typer.Option("-C", "--context", help="Lines of context around fragments")
    ] = 2,
    num_results: Annotated[int, typer.Option("-n", "--num", help="Max results to return")] = 10,
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format: human or json")
    ] = OutputFormat.HUMAN,
) -> None:
    """Full-text search across papers, books, and media.

    \b
    SEARCH MODES (mutually exclusive, one required):
        --paper <id>    Search within a single paper's full text
        --book <id>     Search within a single book's full text
        --all           Search across ALL indexed entries

    \b
    SEARCH TYPE:
        (default)       BM25 keyword search - use keywords like "leadership identity"
        --semantic, -s  Semantic search - use natural language like "How do leaders develop?"

    \b
    OUTPUT OPTIONS:
        --fragments     Show matching text snippets with context
        -C <n>          Context lines around match (default: 2)
        -n <n>          Max results (default: 10)
        --format json   JSON output for scripting

    \b
    EXAMPLES:
        # BM25 keyword search
        paper-index-tool query "leadership identity development" --all

        # Semantic search with natural language question
        paper-index-tool query "How do individuals develop as leaders?" --all -s

        # Semantic search works across languages
        paper-index-tool query "Wat gebeurt er met leiderschap bij thuiswerken?" --all -s

        # Search with context fragments
        paper-index-tool query "qualitative research" --all --fragments -C 3

        # Search single paper, JSON output
        paper-index-tool query "narcissism" --paper cesinger2023 --format json

    \b
    JSON OUTPUT SCHEMA:
        [{"id": "...", "type": "paper|book|media", "score": 0.85, "title": "..."}]

    \b
    NOTE: Semantic search requires AWS Bedrock access. Build vector index first:
        paper-index-tool reindex --vectors
    """
    from paper_index_tool.search import PaperSearcher

    logger.info("Query: %s", search_query)

    # Validate options
    options_count = sum([paper_id is not None, book_id is not None, all_entries])
    if options_count == 0:
        typer.echo(
            "Error: Must specify --paper <id>, --book <id>, or --all. Use --help for examples.",
            err=True,
        )
        raise typer.Exit(1)

    if options_count > 1:
        typer.echo(
            "Error: Cannot use multiple search modes. Choose one of: --paper, --book, or --all.",
            err=True,
        )
        raise typer.Exit(1)

    # Handle book search separately (not yet integrated in searcher)
    if book_id:
        # Search single book
        book = _get_book_or_exit(book_id)
        content = book.get_searchable_text()

        if not content:
            if output_format == OutputFormat.JSON:
                typer.echo(json.dumps([]))
            else:
                typer.echo("No searchable content in book")
            return

        # Use BM25 for scoring
        import bm25s
        import Stemmer

        from paper_index_tool.search import extract_fragments

        stemmer = Stemmer.Stemmer("english")
        corpus_tokens = bm25s.tokenize([content], stopwords="en", stemmer=stemmer)
        query_tokens = bm25s.tokenize([search_query], stopwords="en", stemmer=stemmer)

        retriever = bm25s.BM25()
        retriever.index(corpus_tokens)
        _results_array, scores_array = retriever.retrieve(query_tokens, k=1)

        score = float(scores_array[0, 0])
        if score <= 0:
            if output_format == OutputFormat.JSON:
                typer.echo(json.dumps([]))
            else:
                typer.echo("No results found")
            return

        # Extract fragments if requested
        query_terms = search_query.split()
        frags = []
        if fragments:
            frags = extract_fragments(content, query_terms, context, max_fragments=3)

        if output_format == OutputFormat.JSON:
            book_result: dict[str, Any] = {
                "id": book_id,
                "type": "book",
                "score": score,
                "title": book.title,
            }
            if fragments:
                book_result["fragments"] = frags
            typer.echo(json.dumps([book_result], indent=2))
        else:
            typer.echo(f"[1] {book_id} (score: {score:.4f})")
            typer.echo(f"    Title: {book.title}")

            if fragments and frags:
                for j, frag in enumerate(frags, 1):
                    line_range = f"{frag['line_start']}-{frag['line_end']}"
                    typer.echo(f"\n    Fragment {j} (lines {line_range}):")
                    typer.echo("    " + "-" * 40)
                    for line in frag["lines"]:
                        typer.echo(f"    {line}")

        return

    # Handle semantic search
    if semantic:
        try:
            from paper_index_tool.vector import VectorSearcher
            from paper_index_tool.vector.errors import IndexNotFoundError, VectorSearchError
        except ImportError:
            typer.echo(
                "Error: Vector search dependencies not installed. "
                "Install with: pip install paper-index-tool[vector] or uv sync --extra vector",
                err=True,
            )
            raise typer.Exit(1)

        try:
            vector_searcher = VectorSearcher()
            if not vector_searcher.index_exists():
                typer.echo(
                    "Error: Vector index not found. Build it first with: "
                    "paper-index-tool reindex --vectors",
                    err=True,
                )
                raise typer.Exit(1)

            results = vector_searcher.search(
                query=search_query,
                entry_id=paper_id or book_id,
                top_k=num_results,
                extract_fragments_flag=fragments,
                context_lines=context,
            )
        except IndexNotFoundError:
            typer.echo(
                "Error: Vector index not found. Build it first with: "
                "paper-index-tool reindex --vectors",
                err=True,
            )
            raise typer.Exit(1)
        except VectorSearchError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    # Use CombinedSearcher for --all, PaperSearcher for single paper (BM25)
    elif all_entries:
        from paper_index_tool.search import CombinedSearcher

        combined = CombinedSearcher()
        try:
            results = combined.search(
                query=search_query,
                top_k=num_results,
                extract_fragments_flag=fragments,
                context_lines=context,
            )
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
    else:
        # Single paper search
        try:
            results = PaperSearcher().search(
                query=search_query,
                entry_id=paper_id,
                top_k=num_results,
                extract_fragments_flag=fragments,
                context_lines=context,
            )
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    if output_format == OutputFormat.JSON:
        results_data = []
        for r in results:
            result_item: dict[str, Any] = {
                "id": r.entry_id,
                "type": r.entry_type.value,
                "score": r.score,
                "title": r.entry.title if r.entry else None,
            }
            if fragments:
                result_item["fragments"] = r.fragments
            results_data.append(result_item)
        typer.echo(json.dumps(results_data, indent=2))
    else:
        if not results:
            typer.echo("No results found")
            return

        for i, r in enumerate(results, 1):
            title = r.entry.title if r.entry else "No title"
            typer.echo(f"[{i}] {r.entry_id} (score: {r.score:.4f})")
            typer.echo(f"    Title: {title}")
            if r.entry_type.value != "paper":
                typer.echo(f"    Type: {r.entry_type.value}")

            if fragments and r.fragments:
                for j, frag in enumerate(r.fragments, 1):
                    typer.echo(
                        f"\n    Fragment {j} (lines {frag['line_start']}-{frag['line_end']}):"
                    )
                    typer.echo("    " + "-" * 40)
                    for line in frag["lines"]:
                        typer.echo(f"    {line}")

            typer.echo()


@app.command(name="reindex")
def reindex_command(
    vectors: Annotated[
        bool, typer.Option("--vectors", help="Build vector index (requires AWS Bedrock)")
    ] = False,
    bm25_only: Annotated[
        bool, typer.Option("--bm25", help="Only rebuild BM25 index (skip vectors)")
    ] = False,
) -> None:
    """Rebuild search indices for all entries.

    \b
    INDEX TYPES:
        (default)   Rebuild BM25 keyword search index only
        --vectors   Build vector index for semantic search (requires AWS Bedrock)
        --bm25      Explicitly only rebuild BM25 index

    \b
    USE CASES:
        - After manual edits to JSON files
        - If search results seem stale or incomplete
        - After bulk operations via scripts
        - Before first semantic search (--vectors)

    \b
    NOTE: The 'import' command automatically reindexes BM25.

    \b
    EXAMPLES:
        paper-index-tool reindex              # BM25 only
        paper-index-tool reindex --vectors    # Build vector index (semantic search)

    \b
    REQUIREMENTS FOR --vectors:
        - AWS credentials configured (AWS_PROFILE or environment variables)
        - Bedrock access enabled for amazon.titan-embed-text-v2:0
        - Optional dependencies: pip install paper-index-tool[vector]
    """
    from paper_index_tool.search import CombinedSearcher

    # Build BM25 index (unless --vectors only was intended)
    if not vectors or bm25_only:
        logger.info("Rebuilding BM25 search indices")
        searcher = CombinedSearcher()
        counts = searcher.rebuild_all_indices()
        typer.echo(
            f"BM25: Indexed {counts['papers']} papers, "
            f"{counts['books']} books, {counts['media']} media"
        )

    # Build vector index if requested
    if vectors:
        try:
            from paper_index_tool.vector import VectorSearcher
            from paper_index_tool.vector.errors import AWSCredentialsError, EmbeddingError
        except ImportError:
            typer.echo(
                "Error: Vector search dependencies not installed. "
                "Install with: pip install paper-index-tool[vector] or uv sync --extra vector",
                err=True,
            )
            raise typer.Exit(1)

        typer.echo("Building vector index for semantic search...")
        typer.echo("This requires AWS Bedrock access and may take a few minutes.")

        try:
            vector_searcher = VectorSearcher()
            vector_counts = vector_searcher.rebuild_index()
            typer.echo(
                f"Vector: Indexed {vector_counts['papers']} papers, "
                f"{vector_counts['books']} books, {vector_counts['media']} media "
                f"({vector_counts['chunks']} chunks)"
            )
        except AWSCredentialsError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
        except EmbeddingError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"Error building vector index: {e}", err=True)
            raise typer.Exit(1)


# =============================================================================
# Register Sub-Apps
# =============================================================================


app.add_typer(paper_app, name="paper", help="Paper management commands")
app.add_typer(book_app, name="book", help="Book management commands")
app.add_typer(media_app, name="media", help="Media management commands (video, podcast, blog)")
app.add_typer(completion_app, name="completion")


if __name__ == "__main__":
    app()
