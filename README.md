# paper-index-tool

<p align="center">
  <img src=".github/assets/logo.png" alt="paper-index-tool logo" width="128">
</p>

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://github.com/python/mypy)

A CLI tool for indexing, searching, and managing academic papers, books, and media with BM25 and semantic search.

## Features

- BM25 full-text search across papers, books, and media
- Semantic search using AWS Bedrock embeddings (multi-model support)
- Multiple named vector indices with configurable embedding models
- Structured metadata storage (bibtex fields, abstract, method, results, claims)
- Quick field access for citation validation
- Bibtex export for reference management
- Media support (video, podcast, blog) with timestamp-based quotes

## Installation

```bash
git clone https://github.com/dnvriend/paper-index-tool.git
cd paper-index-tool
uv tool install .
```

## Quick Start

```bash
# Create entry from JSON
paper-index-tool create-from-json ashford2012.json

# View entry
paper-index-tool paper show ashford2012

# BM25 keyword search
paper-index-tool query "leadership identity" --all

# Semantic search (requires vector index)
paper-index-tool vector create my-index --model titan-v2
paper-index-tool vector default my-index
paper-index-tool query "How do leaders develop?" --all --semantic

# Get specific field
paper-index-tool paper claims ashford2012

# Export bibtex
paper-index-tool paper bibtex ashford2012

# View statistics
paper-index-tool stats
```

## Commands

```
paper-index-tool
├── paper           # Paper management (CRUD, field queries, bibtex)
├── book            # Book management (CRUD, field queries, bibtex)
├── media           # Media management (video, podcast, blog)
├── vector          # Vector index management (create, list, delete, default)
├── stats           # Statistics across all entries
├── query           # BM25 or semantic search (--semantic)
├── reindex         # Rebuild search index
├── export          # Export all data to JSON
├── import          # Import from JSON backup
├── create-from-json
├── update-from-json
└── completion      # Shell completion
```

## Documentation

- [Manual](references/manual.md) - Detailed usage guide
- [Vector Search](references/multi-index-vector-search.md) - Multi-index semantic search
- [CLAUDE.md](CLAUDE.md) - Project specification

## Development

```bash
make install    # Install dependencies
make check      # Run all checks (lint, typecheck, test, security)
make pipeline   # Full pipeline
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Author

**Dennis Vriend** - [@dnvriend](https://github.com/dnvriend)
