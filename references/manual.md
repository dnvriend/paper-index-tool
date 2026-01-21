# paper-index-tool Manual

Comprehensive usage guide for paper-index-tool.

## Table of Contents

- [Paper Management](#paper-management)
- [Book Management](#book-management)
- [Media Management](#media-management)
- [Search](#search)
- [Import/Export](#importexport)
- [Multi-Level Verbosity Logging](#multi-level-verbosity-logging)
- [OpenTelemetry Observability](#opentelemetry-observability)
- [Shell Completion](#shell-completion)

## Paper Management

### CRUD Operations

```bash
paper-index-tool paper create <id> [--field value...]
paper-index-tool paper show <id> [--format json]
paper-index-tool paper update <id> [--field value...]
paper-index-tool paper delete <id> [--force]
paper-index-tool paper list [--format json] [--count]
paper-index-tool paper clear --approve
```

### Field Queries

Quick access for citation validation:

```bash
paper-index-tool paper abstract <id>
paper-index-tool paper question <id>
paper-index-tool paper method <id>
paper-index-tool paper gaps <id>
paper-index-tool paper results <id>
paper-index-tool paper claims <id>
paper-index-tool paper quotes <id>
paper-index-tool paper file-path-pdf <id>
paper-index-tool paper file-path-md <id>
```

### Search and Export

```bash
paper-index-tool paper query <id> "search terms" [--fragments]
paper-index-tool paper bibtex <id>
```

## Book Management

Same structure as papers:

```bash
paper-index-tool book create <id> [--field value...]
paper-index-tool book show <id>
paper-index-tool book update <id> [--field value...]
paper-index-tool book delete <id> [--force]
paper-index-tool book list [--format json]
paper-index-tool book bibtex <id>
```

## Media Management

Supports video, podcast, and blog content.

### Create Media

```bash
paper-index-tool media create tedtalk2023 \
    --type video --author "TEDx" --title "Leadership Talk" \
    --year 2023 --url "https://..." --access-date "2024-01-15" \
    --file-path-md "/path/to/transcript.md" ...
```

### Type-Specific Fields

- **video**: `--platform`, `--channel`, `--duration`, `--video-id`
- **podcast**: `--show-name`, `--episode`, `--season`, `--host`, `--guest`
- **blog**: `--website`, `--last-updated`

### AI Tracking

```bash
--ai-generated --ai-provider "Anthropic" --ai-model "claude-3"
```

### Media Operations

```bash
paper-index-tool media show <id>
paper-index-tool media list [--type video|podcast|blog]
paper-index-tool media transcript <id>
paper-index-tool media quotes <id>
```

## Search

BM25 full-text search across all indexed content.

```bash
# Search all entries
paper-index-tool query "leadership identity" --all

# Search with fragments and context
paper-index-tool query "qualitative research" --all --fragments -C 3 -n 5

# Search single entry
paper-index-tool query "narcissism" --paper cesinger2023

# JSON output for scripting
paper-index-tool query "organizational behavior" --all --format json
```

## Import/Export

### Backup and Restore

```bash
# Export all data
paper-index-tool export backup.json

# Import (replace all existing)
paper-index-tool import backup.json

# Import (merge, keep existing)
paper-index-tool import new-papers.json --merge

# Preview import
paper-index-tool import backup.json --dry-run
```

### JSON Entry Files

```bash
# Create entry from JSON file
paper-index-tool create-from-json ashford2012.json

# Update entry from JSON file
paper-index-tool update-from-json ashford2012.json

# Rebuild search index
paper-index-tool reindex
```

## Multi-Level Verbosity Logging

All logs output to stderr, keeping stdout clean for data piping.

| Flag | Level | Output | Use Case |
|------|-------|--------|----------|
| (none) | WARNING | Errors and warnings only | Production |
| `-v` | INFO | + High-level operations | Normal debugging |
| `-vv` | DEBUG | + Detailed info | Development |
| `-vvv` | TRACE | + Library internals | Deep debugging |

```bash
paper-index-tool stats                    # Quiet mode
paper-index-tool -v query "test" --all    # See operations
paper-index-tool -vv paper show id        # Detailed logging
```

## OpenTelemetry Observability

Optional tracing, metrics, and logs integration with Grafana stack.

### Installation

```bash
uv sync --extra telemetry
```

### Enable Telemetry

```bash
# Via CLI flag
paper-index-tool --telemetry query "test" --all

# Via environment
export OTEL_ENABLED=true
export OTEL_EXPORTER_TYPE=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
paper-index-tool query "test" --all
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_ENABLED` | `false` | Enable telemetry |
| `OTEL_SERVICE_NAME` | `paper-index-tool` | Service name |
| `OTEL_EXPORTER_TYPE` | `console` | `console` or `otlp` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP endpoint |

## Shell Completion

### Quick Setup

```bash
# Bash
eval "$(paper-index-tool completion generate bash)"

# Zsh
eval "$(paper-index-tool completion generate zsh)"

# Fish
paper-index-tool completion generate fish | source
```

### Permanent Setup

```bash
# Bash - add to ~/.bashrc
echo 'eval "$(paper-index-tool completion generate bash)"' >> ~/.bashrc

# Zsh - add to ~/.zshrc
echo 'eval "$(paper-index-tool completion generate zsh)"' >> ~/.zshrc

# Fish - save to completions directory
mkdir -p ~/.config/fish/completions
paper-index-tool completion generate fish > ~/.config/fish/completions/paper-index-tool.fish
```
