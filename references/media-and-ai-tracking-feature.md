# Feature Specification: Media Category & AI Generation Tracking

## Overview

Extend paper-index-tool with:
1. New `Media` category for video, podcast, and blog sources
2. AI generation tracking fields across all categories (paper, book, media)

## Rationale

- Academic sources increasingly include non-traditional media (YouTube lectures, podcasts, blogs)
- AI-generated content is now acceptable as academic sources (anno 2026)
- Need to track provenance for citation integrity

---

## Part 1: AI Generation Tracking

### New Fields (All Categories)

Add to Paper, Book, and Media models:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ai_generated` | `bool` | `False` | Whether content was AI-generated |
| `ai_provider` | `str \| None` | `None` | AI service provider (if ai_generated=True) |
| `ai_model` | `str \| None` | `None` | Specific model used (if ai_generated=True) |

### AI Provider Values

Enum or validated string with allowed values:
- `anthropic` - Claude models
- `openai` - GPT models
- `google` - Gemini models
- `meta` - Llama models
- `mistral` - Mistral models
- `other` - Other providers

### AI Model Examples

Free-form string for model identification:
- `claude-3-opus-20240229`
- `claude-sonnet-4-20250514`
- `gpt-4o-2024-08-06`
- `gemini-2.0-flash`
- `llama-3.1-405b`

### BibTeX Export

Add to bibtex output when `ai_generated=True`:

```bibtex
@article{example2025,
  ...
  note = {AI-generated content using Anthropic Claude claude-sonnet-4-20250514},
}
```

### Validation Rules

- If `ai_generated=True`, then `ai_provider` should be set
- If `ai_provider` is set, `ai_model` is recommended but optional
- If `ai_generated=False`, both `ai_provider` and `ai_model` should be None

---

## Part 2: Media Model

### Media Types

Enum with allowed values:

| Type | BibTeX | Use Case |
|------|--------|----------|
| `video` | `@misc` | YouTube, Vimeo, educational videos |
| `podcast` | `@misc` | Audio content with transcripts |
| `blog` | `@online` | Website articles, blog posts |

### Media Model Fields

#### Identity & Type
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `str` | Yes | Unique ID: `<surname><year>[suffix]` |
| `media_type` | `MediaType` | Yes | `video`, `podcast`, or `blog` |

#### Core BibTeX Fields (All Media Types)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `author` | `str` | Yes | Creator/speaker/host name(s) |
| `title` | `str` | Yes | Title of video/episode/post |
| `year` | `int` | Yes | Publication year |
| `url` | `str` | Yes | Primary URL (required for media) |
| `access_date` | `date` | Yes | Date accessed (important for web sources) |
| `keywords` | `str` | No | Comma-separated keywords |
| `rating` | `int` | No | Quality rating 1-5 |

#### Video-Specific Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | `str` | No | Platform name (YouTube, Vimeo, etc.) |
| `channel` | `str` | No | Channel/creator name |
| `duration` | `str` | No | Duration in HH:MM:SS or MM:SS |
| `video_id` | `str` | No | Platform-specific video ID |

#### Podcast-Specific Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `show_name` | `str` | No | Podcast show/series name |
| `episode` | `str` | No | Episode number or identifier |
| `season` | `str` | No | Season number |
| `host` | `str` | No | Host name(s) |
| `guest` | `str` | No | Guest name(s) |
| `duration` | `str` | No | Duration in HH:MM:SS or MM:SS |

#### Blog-Specific Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `website` | `str` | No | Website/publication name |
| `last_updated` | `date` | No | Last update date |

#### File Paths
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_path_markdown` | `str` | Yes | Path to transcript/content markdown |
| `file_path_pdf` | `str` | No | Path to PDF (if available) |
| `file_path_media` | `str` | No | Path to downloaded media file |

#### Content Fields (Same as Paper/Book)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `abstract` | `str` | Yes | Summary (max 1000 words) |
| `question` | `str` | Yes | Main topic/question addressed |
| `method` | `str` | Yes | Approach/structure |
| `gaps` | `str` | Yes | Limitations |
| `results` | `str` | Yes | Key points/findings |
| `interpretation` | `str` | Yes | Analysis/implications |
| `claims` | `str` | Yes | Verifiable claims |
| `quotes` | `list[Quote]` | Yes | Verbatim quotes with timestamps |
| `full_text` | `str` | Yes | Full transcript/content |

#### AI Generation Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ai_generated` | `bool` | No | AI-generated content flag |
| `ai_provider` | `str` | No | AI provider if generated |
| `ai_model` | `str` | No | AI model if generated |

### Quote Model Extension

For media, quotes may use timestamps instead of page numbers:

```python
class Quote(BaseModel):
    text: str
    page: int | None = None      # For papers/books
    timestamp: str | None = None  # For video/podcast (HH:MM:SS)
```

### BibTeX Export

#### Video
```bibtex
@misc{ashford2017,
  author = {Ashford, Susan J.},
  title = {Why Everyone Should See Themselves as a Leader},
  year = {2017},
  howpublished = {YouTube video},
  url = {https://youtube.com/watch?v=...},
  urldate = {2025-01-21},
  note = {HBR IdeaCast, Duration: 25:30}
}
```

#### Podcast
```bibtex
@misc{ashford2017,
  author = {Ashford, Susan J.},
  title = {Why Everyone Should See Themselves as a Leader},
  year = {2017},
  howpublished = {Podcast},
  url = {https://hbr.org/podcast/...},
  urldate = {2025-01-21},
  note = {HBR IdeaCast, Episode August 2017, Host: Sarah Green Carmichael}
}
```

#### Blog
```bibtex
@online{smith2025,
  author = {Smith, John},
  title = {Understanding Modern Leadership},
  year = {2025},
  url = {https://example.com/blog/...},
  urldate = {2025-01-21},
  organization = {Leadership Today Blog}
}
```

---

## Part 3: CLI Commands

### Media Commands

```bash
# Create
paper-index-tool media create <id> --type video|podcast|blog [--field value...]

# Show
paper-index-tool media show <id> [--format human|json]

# Update
paper-index-tool media update <id> [--field value...]

# Delete
paper-index-tool media delete <id> [--force]

# List
paper-index-tool media list [--type video|podcast|blog] [--format human|json]

# Quick field access
paper-index-tool media abstract <id>
paper-index-tool media claims <id>
paper-index-tool media transcript <id>  # alias for full_text

# Export
paper-index-tool media bibtex <id>
```

### AI Tracking Options (All Categories)

```bash
# Create with AI tracking
paper-index-tool paper create <id> --ai-generated --ai-provider anthropic --ai-model claude-sonnet-4

# Update AI tracking
paper-index-tool paper update <id> --ai-generated true --ai-provider openai --ai-model gpt-4o

# Filter by AI generated
paper-index-tool paper list --ai-generated
paper-index-tool book list --ai-generated
paper-index-tool media list --ai-generated
```

### Global Stats Update

```bash
paper-index-tool stats
# Output:
# Papers: 42 (3 AI-generated)
# Books: 11 (0 AI-generated)
# Media: 5 (2 AI-generated)
#   - Videos: 2
#   - Podcasts: 2
#   - Blogs: 1
# Total: 58 entries
```

---

## Part 4: Data Storage

### File Structure

```
~/.config/paper-index-tool/
├── papers.json      # Paper entries
├── books.json       # Book entries
├── media.json       # Media entries (NEW)
└── bm25s/           # Search index (includes all types)
```

### JSON Schema Example (Media)

```json
{
  "ashford2017": {
    "id": "ashford2017",
    "media_type": "podcast",
    "author": "Ashford, Susan J.",
    "title": "Why Everyone Should See Themselves as a Leader",
    "year": 2017,
    "url": "https://hbr.org/podcast/2017/08/why-everyone-should-see-themselves-as-a-leader",
    "access_date": "2025-01-21",
    "show_name": "HBR IdeaCast",
    "host": "Sarah Green Carmichael",
    "duration": "25:30",
    "file_path_markdown": "/path/to/transcript.md",
    "abstract": "...",
    "claims": "...",
    "quotes": [
      {"text": "...", "timestamp": "05:30"},
      {"text": "...", "timestamp": "12:45"}
    ],
    "full_text": "...",
    "ai_generated": false,
    "ai_provider": null,
    "ai_model": null,
    "created_at": "2025-01-21T10:00:00",
    "updated_at": "2025-01-21T10:00:00"
  }
}
```

---

## Part 5: Implementation Plan

### Phase 1: AI Generation Fields
1. Add `ai_generated`, `ai_provider`, `ai_model` to Paper model
2. Add same fields to Book model
3. Update CLI options for create/update commands
4. Update bibtex export to include AI note
5. Update stats command
6. Add tests

### Phase 2: Media Model
1. Create `MediaType` enum
2. Create `Media` model with all fields
3. Extend `Quote` model with timestamp support
4. Create `media.json` registry
5. Add CLI commands (media subcommand)
6. Update search index to include media
7. Update stats command
8. Add tests

### Phase 3: Migration & Documentation
1. Migrate existing podcast entries (ashford2017) to media
2. Update CLAUDE.md with new commands
3. Update skill prompts for media entries
4. Add examples to documentation

---

## Part 6: Validation Summary

### Paper (Updated)
- All existing validations remain
- New: `ai_provider` must be from allowed list if set
- New: `ai_model` is free-form string

### Book (Updated)
- All existing validations remain
- New: Same AI validation as Paper

### Media (New)
- `id`: Same format as paper/book
- `media_type`: Must be video, podcast, or blog
- `url`: Required (unlike paper/book where it's optional)
- `access_date`: Required
- `author`, `title`, `year`: Required
- Content fields: Same validation as paper/book
- `quotes`: Allow timestamp instead of page number

---

## Open Questions

1. Should we allow mixed timestamp/page in quotes for media that have both video and PDF?
2. Should `access_date` auto-populate with current date if not provided?
3. Should we validate URL reachability on create?
4. Should platform-specific validation exist (e.g., YouTube URL format)?
