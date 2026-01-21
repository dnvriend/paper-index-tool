# paper-index-tool - Project Specification

## Goal

A Python CLI tool for indexing, searching, and managing academic paper, book, and media metadata and content.

## What is paper-index-tool?

`paper-index-tool` is a command-line utility that provides:

- **Searchable index** of academic papers, books, and media with BM25 full-text search
- **Structured metadata storage** for bibtex fields and content (abstract, method, results, claims, etc.)
- **Quick field access** for citation validation and reference management
- **Bibtex export** for integration with LaTeX and reference managers
- **Media support** for video, podcast, and blog content with timestamp-based quotes

## Technical Requirements

### Runtime

- Python 3.14+
- Installable globally with mise
- Cross-platform (macOS, Linux, Windows)

### Dependencies

- `typer` - CLI framework (built on Click with type hints)
- `pydantic` - Data validation and serialization
- `bm25s` - BM25 search algorithm (Rust-based)
- `PyStemmer` - Stemming for search tokenization

### Optional Dependencies

- `opentelemetry-api` - OpenTelemetry API
- `opentelemetry-sdk` - OpenTelemetry SDK
- `opentelemetry-exporter-otlp` - OTLP exporter for Grafana Alloy/OTEL Collector

### Development Dependencies

- `ruff` - Linting and formatting
- `mypy` - Type checking
- `pytest` - Testing framework
- `bandit` - Security linting
- `pip-audit` - Dependency vulnerability scanning
- `gitleaks` - Secret detection (requires separate installation)

## CLI Commands

### Global Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Verbosity level: -v=INFO, -vv=DEBUG, -vvv=TRACE |
| `--telemetry` | Enable OpenTelemetry (or set OTEL_ENABLED=true) |
| `--help` / `-h` | Show help message |
| `--version` | Show version |

### Command Structure

```
paper-index-tool
├── paper              # Paper management
│   ├── create, show, update, delete, list, clear
│   ├── abstract, question, method, gaps, results, claims, quotes
│   ├── file-path-pdf, file-path-md, bibtex, query
├── book               # Book management (same structure as paper)
├── media              # Media management (video, podcast, blog)
│   ├── create, show, update, delete, list, clear
│   ├── abstract, question, method, gaps, results, claims, quotes
│   ├── transcript, file-path-md, bibtex, query
├── stats              # Statistics across all entries
├── query              # BM25 search across all entries
├── reindex            # Rebuild search index
├── export             # Export all data to JSON
├── import             # Import from JSON backup
├── create-from-json   # Create entry from JSON file
├── update-from-json   # Update entry from JSON file
└── completion         # Shell completion
```

### Paper Commands

```bash
# CRUD
paper-index-tool paper create <id> [--field value...]
paper-index-tool paper show <id> [--format json]
paper-index-tool paper update <id> [--field value...]
paper-index-tool paper delete <id> [--force]
paper-index-tool paper list [--format json] [--count]
paper-index-tool paper clear --approve

# Field queries (quick access)
paper-index-tool paper abstract <id>
paper-index-tool paper question <id>
paper-index-tool paper method <id>
paper-index-tool paper gaps <id>
paper-index-tool paper results <id>
paper-index-tool paper claims <id>
paper-index-tool paper quotes <id>
paper-index-tool paper file-path-pdf <id>
paper-index-tool paper file-path-md <id>

# Export and search
paper-index-tool paper bibtex <id>
paper-index-tool paper query <id> "search terms" [--fragments]
```

### Media Commands

```bash
# Create (required: --type, --author, --title, --year, --url, --access-date, --file-path-md)
paper-index-tool media create <id> --type video|podcast|blog ...

# Type-specific fields:
# - video: --platform, --channel, --duration, --video-id
# - podcast: --show-name, --episode, --season, --host, --guest
# - blog: --website, --last-updated

# AI tracking fields: --ai-generated, --ai-provider, --ai-model
```

### Search Commands

```bash
# Search all entries
paper-index-tool query "search terms" --all [--fragments] [-C <context>] [-n <num>]

# Search single entry
paper-index-tool query "search terms" --paper <id>
paper-index-tool query "search terms" --book <id>

# Rebuild search index
paper-index-tool reindex
```

### Import/Export

```bash
paper-index-tool export backup.json [--force]
paper-index-tool import backup.json [--replace|--merge] [--dry-run]
paper-index-tool create-from-json entry.json
paper-index-tool update-from-json entry.json
```

### Data Models

**Paper Fields**:
- Bibtex: author, title, year, journal, volume, number, issue, pages, publisher, doi, url
- Files: file_path_pdf, file_path_markdown
- Meta: keywords, rating (1-5), peer_reviewed
- Content: abstract, question, method, gaps, results, interpretation, claims, quotes, full_text

**Book Fields**:
- Bibtex: author, title, year, chapter, pages, publisher, isbn, url
- Files: file_path_pdf, file_path_markdown
- Meta: keywords
- Content: (same as paper)

**Media Fields**:
- Core: media_type (video|podcast|blog), author, title, year, url, access_date
- Video: platform, channel, duration, video_id
- Podcast: show_name, episode, season, host, guest, duration
- Blog: website, last_updated
- AI: ai_generated, ai_provider, ai_model
- Content: (same as paper, with timestamp-based quotes)

## Data Storage

| Path | Description |
|------|-------------|
| `~/.config/paper-index-tool/papers.json` | Paper entries |
| `~/.config/paper-index-tool/books.json` | Book entries |
| `~/.config/paper-index-tool/media.json` | Media entries |
| `~/.config/paper-index-tool/bm25s/` | BM25 search index |

## Project Structure

```
paper-index-tool/
├── paper_index_tool/
│   ├── __init__.py
│   ├── cli.py              # Typer CLI entry point (~3500 lines)
│   ├── models.py           # Paper, Book, Media, Quote Pydantic models
│   ├── search.py           # BM25 search (PaperSearcher, BookSearcher, CombinedSearcher)
│   ├── completion.py       # Shell completion (bash, zsh, fish)
│   ├── logging_config.py   # Multi-level verbosity logging
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── paths.py        # Config paths (~/.config/paper-index-tool/)
│   │   └── registry.py     # PaperRegistry, BookRegistry, MediaRegistry
│   ├── telemetry/          # OpenTelemetry (optional)
│   │   ├── config.py       # TelemetryConfig
│   │   ├── service.py      # TelemetryService singleton
│   │   ├── decorators.py   # @traced, trace_span
│   │   └── exporters.py    # Console, OTLP exporters
│   └── utils.py
├── tests/
├── references/             # Feature specs, observability stack configs
├── .claude/commands/       # Slash commands for Claude
├── pyproject.toml
├── README.md
├── CLAUDE.md
└── Makefile
```

## Code Style

- Type hints for all functions
- Docstrings for all public functions
- Follow PEP 8 via ruff
- 100 character line length
- Strict mypy checking

## Development Workflow

```bash
# Install dependencies
make install

# Run linting
make lint

# Format code
make format

# Type check
make typecheck

# Run tests
make test

# Security scanning
make security-bandit       # Python security linting
make security-pip-audit    # Dependency CVE scanning
make security-gitleaks     # Secret detection
make security              # Run all security checks

# Run all checks (includes security)
make check

# Full pipeline (includes security)
make pipeline
```

## Security

The template includes three lightweight security tools:

1. **bandit** - Python code security linting
   - Detects: SQL injection, hardcoded secrets, unsafe functions
   - Speed: ~2-3 seconds

2. **pip-audit** - Dependency vulnerability scanning
   - Detects: Known CVEs in dependencies
   - Speed: ~2-3 seconds

3. **gitleaks** - Secret and API key detection
   - Detects: AWS keys, GitHub tokens, API keys, private keys
   - Speed: ~1 second
   - Requires: `brew install gitleaks` (macOS)

All security checks run automatically in `make check` and `make pipeline`.

## Multi-Level Verbosity Logging

The template includes a centralized logging system with progressive verbosity levels and optional file logging.

### Implementation Pattern

1. **logging_config.py** - Centralized logging configuration
   - `setup_logging(verbose_count, log_file, log_format)` - Configure logging
   - `get_logger(name)` - Get logger instance for module
   - Maps verbosity to Python logging levels (WARNING/INFO/DEBUG)
   - Supports file logging with rotation (10MB, 5 backups)

2. **CLI Integration** - Add to every CLI command
   ```python
   from typing import Annotated
   import typer
   from paper_index_tool.logging_config import get_logger, setup_logging

   logger = get_logger(__name__)

   @app.command()
   def command(
       verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, help="...")] = 0,
   ) -> None:
       setup_logging(verbose)  # First thing in command
       logger.info("Operation started")
       logger.debug("Detailed info")
   ```

3. **Logging Levels**
   - **0 (no -v)**: WARNING only - production/quiet mode
   - **1 (-v)**: INFO - high-level operations
   - **2 (-vv)**: DEBUG - detailed debugging
   - **3+ (-vvv)**: TRACE - enable library internals

4. **File Logging**

   Enable file logging via environment variable or argument:
   ```bash
   # Via environment
   export LOG_FILE=/var/log/paper-index-tool.log
   paper-index-tool -v

   # Or programmatically
   setup_logging(verbose_count=1, log_file="/var/log/app.log")
   ```

   File logging features:
   - Rotating file handler (10MB max, 5 backups)
   - Creates parent directories automatically
   - Includes timestamps in log format
   - Custom format via `LOG_FORMAT` env var

5. **Environment Variables**

   | Variable | Default | Description |
   |----------|---------|-------------|
   | `LOG_FILE` | (none) | Path to log file (enables file logging) |
   | `LOG_FORMAT` | (default) | Custom log format string |

6. **Best Practices**
   - Always log to stderr (keeps stdout clean for piping)
   - Use structured messages with placeholders: `logger.info("Found %d items", count)`
   - Call `setup_logging()` first in every command
   - Use `get_logger(__name__)` at module level
   - For TRACE level, enable third-party library loggers in `logging_config.py`

7. **Customizing Library Logging**
   Edit `logging_config.py` to add project-specific libraries:
   ```python
   if verbose_count >= 3:
       logging.getLogger("requests").setLevel(logging.DEBUG)
       logging.getLogger("urllib3").setLevel(logging.DEBUG)
   ```

## OpenTelemetry Observability

The template includes OpenTelemetry integration for traces, metrics, and logs. Designed for Grafana stack (Alloy, Tempo, Prometheus, Loki).

### Installation

```bash
# Install with telemetry support
pip install paper-index-tool[telemetry]
# or with uv
uv sync --extra telemetry
```

### Enabling Telemetry

```bash
# Via CLI flag
paper-index-tool --telemetry

# Via environment variable
export OTEL_ENABLED=true
paper-index-tool
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_ENABLED` | `false` | Enable telemetry |
| `OTEL_SERVICE_NAME` | `paper-index-tool` | Service name in traces |
| `OTEL_EXPORTER_TYPE` | `console` | `console` or `otlp` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | Alloy/Collector endpoint |
| `OTEL_EXPORTER_OTLP_INSECURE` | `true` | Use insecure connection |

### Architecture (SOLID Design)

```
telemetry/
├── config.py      # TelemetryConfig - configuration from env vars (SRP)
├── service.py     # TelemetryService - singleton facade (ISP, DIP)
├── decorators.py  # @traced, trace_span - tracing utilities
└── exporters.py   # Exporter factory - extensible backends (OCP)
```

### Usage Patterns

**1. @traced Decorator**
```python
from paper_index_tool.telemetry import traced

@traced("process_data")
def process_data(items: list) -> dict:
    return {"count": len(items)}

@traced(attributes={"operation.type": "batch"})
def batch_process():
    pass
```

**2. trace_span Context Manager**
```python
from paper_index_tool.telemetry import trace_span

with trace_span("database_query", {"db.system": "postgres"}) as span:
    result = db.execute(query)
    if span:
        span.set_attribute("db.rows", len(result))
```

**3. Custom Metrics**
```python
from paper_index_tool.telemetry import TelemetryService

meter = TelemetryService.get_instance().meter
counter = meter.create_counter("items_processed", description="Items processed")
counter.add(100, {"type": "batch"})

histogram = meter.create_histogram("processing_duration", unit="ms")
histogram.record(150.5, {"operation": "transform"})
```

### Grafana Stack Integration

**Push to Grafana Alloy (recommended)**
```bash
export OTEL_ENABLED=true
export OTEL_EXPORTER_TYPE=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
paper-index-tool
```

### Local Observability Stack

A complete local observability stack is included in `references/`:

```bash
# Start the stack
cd references
docker compose up -d

# Configure your CLI
export OTEL_ENABLED=true
export OTEL_EXPORTER_TYPE=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
paper-index-tool -v
```

Access Grafana at http://localhost:3000 (admin/admin).

**Stack Components:**

| Service | Port | Description |
|---------|------|-------------|
| Grafana Alloy | 4317, 4318 | OTLP receiver |
| Tempo | 3200 | Distributed tracing |
| Prometheus | 9090 | Metrics storage |
| Loki | 3100 | Log aggregation |
| Grafana | 3000 | Visualization |

**Data Flow:**
```
paper-index-tool --telemetry
      │ OTLP
      ▼
   Alloy ──► Tempo (traces)
      │
      ├────► Prometheus (metrics)
      │
      └────► Loki (logs)
              │
              ▼
           Grafana
```

See `references/README.md` for detailed configuration options.

### Development Mode

For development, use console exporter (default):
```bash
paper-index-tool --telemetry -vv
```

This outputs traces, metrics, and logs to stderr.

## Shell Completion

The template includes shell completion for bash, zsh, and fish using Typer's completion system.

### Implementation

1. **completion.py** - Separate module for completion command
   - Uses Click's `BashComplete`, `ZshComplete`, `FishComplete` classes (Typer is built on Click)
   - Generates shell-specific completion scripts
   - Includes installation instructions in help text

2. **CLI Integration** - Added as sub-app
   ```python
   from paper_index_tool.completion import completion_app

   app = typer.Typer(invoke_without_command=True)

   @app.callback(invoke_without_command=True)
   def main(ctx: typer.Context) -> None:
       # Default behavior when no subcommand
       if ctx.invoked_subcommand is None:
           # Main command logic here
           pass

   # Add completion sub-app
   app.add_typer(completion_app, name="completion")
   ```

3. **Usage Pattern** - User-friendly command
   ```bash
   # Generate completion script
   paper-index-tool completion generate bash
   paper-index-tool completion generate zsh
   paper-index-tool completion generate fish

   # Install (eval or save to file)
   eval "$(paper-index-tool completion generate bash)"
   ```

4. **Supported Shells**
   - **Bash** (≥ 4.4) - Uses bash-completion
   - **Zsh** (any recent) - Uses zsh completion system
   - **Fish** (≥ 3.0) - Uses fish completion system
   - **PowerShell** - Not supported

5. **Installation Methods**
   - **Temporary**: `eval "$(paper-index-tool completion generate bash)"`
   - **Permanent**: Add eval to ~/.bashrc or ~/.zshrc
   - **File-based** (recommended): Save to dedicated completion file

### Adding More Commands

The CLI uses `typer.Typer()` for extensibility. To add new commands:

1. Create new command module in `paper_index_tool/`
2. Import and add to CLI app:
   ```python
   from paper_index_tool.new_command import new_command
   app.command()(new_command)
   # Or for sub-apps:
   app.add_typer(new_app, name="subcommand")
   ```

3. Completion will automatically work for new commands and their options

## Installation Methods

### Global installation with mise

```bash
cd /path/to/paper-index-tool
mise use -g python@3.14
uv sync
uv tool install .
```

After installation, `paper-index-tool` command is available globally.

### Local development

```bash
uv sync
uv run paper-index-tool [args]
```

## Publishing to PyPI

The template includes GitHub Actions workflow for automated PyPI publishing with trusted publishing (no API tokens required).

### Setup PyPI Trusted Publishing

1. **Create PyPI Account** at https://pypi.org/account/register/
   - Enable 2FA (required)
   - Verify email

2. **Configure Trusted Publisher** at https://pypi.org/manage/account/publishing/
   - Click "Add a new pending publisher"
   - **PyPI Project Name**: `paper-index-tool`
   - **Owner**: `dnvriend`
   - **Repository name**: `paper-index-tool`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`

3. **(Optional) Configure TestPyPI** at https://test.pypi.org/manage/account/publishing/
   - Same settings but use environment: `testpypi`

### Publishing Workflow

The `.github/workflows/publish.yml` workflow:
- Builds on every push
- Publishes to TestPyPI and PyPI on git tags (v*)
- Uses trusted publishing (no secrets needed)

### Create a Release

```bash
# Commit your changes
git add .
git commit -m "Release v0.1.0"
git push

# Create and push tag
git tag v0.1.0
git push origin v0.1.0
```

The workflow automatically builds and publishes to PyPI.

### Install from PyPI

After publishing, users can install with:

```bash
pip install paper-index-tool
```

### Build Locally

```bash
# Build package with force rebuild (avoids cache issues)
make build

# Output in dist/
ls dist/
```
