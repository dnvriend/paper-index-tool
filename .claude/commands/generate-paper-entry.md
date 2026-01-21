# Generate Paper Entry

Generate a JSON entry file for an academic paper that can be imported using `paper-index-tool create-from-json`.

## Input

Provide the markdown file path containing the full text of an academic paper.

## Output

A JSON file saved as `<paper_id>.json` in the same directory as the source markdown file.

## Field Extraction Rules

### Identity Field

- **id**: `<first_author_surname><year>` (lowercase), e.g., "ashford2012"
  - Multiple papers same author/year: append letter "ashford2012a", "ashford2012b"

### Bibtex Metadata (extract from paper header)

| Field | Description |
|-------|-------------|
| author | Full names in "Last, First" format, separated by " and " |
| title | Full paper title |
| year | 4-digit publication year |
| journal | Journal name |
| volume | Volume number |
| number | Number within volume |
| issue | Issue number |
| pages | Page range (e.g., "219-235") |
| publisher | Publisher name |
| doi | Digital Object Identifier |
| url | URL (optional, null if unavailable) |
| keywords | Comma-separated (extract or generate) |
| rating | Set to 3 (neutral default) |
| peer_reviewed | true for journal articles |

### File Paths (derive from input)

| Field | Value |
|-------|-------|
| file_path_pdf | Same path as markdown with .pdf extension |
| file_path_markdown | Input markdown file (absolute path) |

### Content Fields

| Field | Rules |
|-------|-------|
| abstract | Verbatim from paper (max 1000 words) |
| question | Research question(s), 600-1000 words if source >1000 |
| method | Methodology, 600-1000 words if source >1000 |
| gaps | Limitations/gaps, 600-1000 words if source >1000 |
| results | Key findings, 600-1000 words if source >1000 |
| interpretation | Discussion/implications, 600-1000 words if source >1000 |
| claims | Verifiable claims as bullet list, 600-1000 words if source >1000 |
| quotes | Minimum 10 entries, each 50-200 words with page reference |
| full_text | **DO NOT include** - auto-populated from file_path_markdown |

## JSON Schema

```json
{
  "id": "authorname2024",
  "author": "Last, First and Last2, First2",
  "title": "Full Paper Title",
  "year": 2024,
  "journal": "Journal Name",
  "volume": "42",
  "number": "3",
  "issue": "3",
  "pages": "100-125",
  "publisher": "Publisher Name",
  "doi": "10.1234/example.2024.001",
  "url": "https://doi.org/10.1234/example.2024.001",
  "file_path_pdf": "/absolute/path/to/paper.pdf",
  "file_path_markdown": "/absolute/path/to/paper.md",
  "keywords": "keyword1, keyword2, keyword3",
  "rating": 3,
  "peer_reviewed": true,
  "abstract": "Verbatim abstract...",
  "question": "Research question(s)...",
  "method": "Methodology...",
  "gaps": "Limitations...",
  "results": "Key findings...",
  "interpretation": "Discussion...",
  "claims": "- Claim 1\n- Claim 2\n- ...",
  "quotes": [
    {"text": "Quote text (50-200 words)...", "page": 102},
    {"text": "Another quote...", "page": 105}
  ]
}
```

## Validation Checklist

Before outputting JSON:

- [ ] id: `<surname><year>[a-z]?` format (lowercase)
- [ ] author: min 2 characters
- [ ] title: min 5 characters
- [ ] year: 4-digit between 1900 and current+1
- [ ] journal, volume, number, issue, pages, publisher: min 1 character
- [ ] doi: min 2 characters
- [ ] url: starts with http(s):// or null
- [ ] file_path_*: absolute paths starting with / or ~
- [ ] Content fields: each under 1000 words
- [ ] quotes: 10+ entries, each 50-200 words with positive page number
- [ ] full_text: NOT included (auto-populated)

## Workflow

1. User provides: `/path/to/paper.md`
2. Read markdown file
3. Extract metadata from paper header
4. Process content fields per rules above
5. Generate JSON with:
   - `file_path_markdown`: input path
   - `file_path_pdf`: same path with .pdf extension
6. Save to `/path/to/paper_id.json`
7. User runs: `paper-index-tool create-from-json /path/to/paper_id.json`

## Notes

- Use absolute file paths
- Preserve academic rigor in summaries
- When summarizing, prioritize: findings, methodology, statistics, theory
- Select diverse quotes covering different sections
- If metadata unclear, make reasonable inferences
