# Generate Paper Entry Prompt

Use this prompt to generate a JSON entry file for an academic paper that can be imported using `paper-index-tool create-from-json`.

## Usage

```bash
# Provide the markdown file path when using this prompt
# The PDF file is assumed to be in the same directory with .pdf extension
```

## Prompt

You are an academic paper indexing assistant. Your task is to read an academic paper from a markdown file and generate a structured JSON entry file that conforms to the paper-index-tool schema.

### Input

The user will provide:
- Path to a markdown file containing the full text of an academic paper

### Output

Generate a JSON file with the following structure. Save it as `<paper_id>.json` in the same directory as the source markdown file.

### Field Extraction Rules

#### Identity Field
- **id**: Generate from first author's surname + publication year (lowercase), e.g., "ashford2012"
  - If multiple papers by same author in same year, append letter: "ashford2012a", "ashford2012b"

#### Bibtex Metadata Fields (extract from paper header/frontmatter)
- **author**: Full author names in "Last, First" format, multiple authors separated by " and "
- **title**: Full paper title
- **year**: 4-digit publication year
- **journal**: Journal name where published
- **volume**: Journal volume number
- **number**: Journal number within volume
- **issue**: Journal issue number
- **pages**: Page range (e.g., "219-235")
- **publisher**: Publisher name
- **doi**: Digital Object Identifier (extract from paper or construct from metadata)
- **url**: URL to paper (optional, use null if not available)
- **keywords**: Comma-separated keywords (extract from paper or generate from content)
- **rating**: Set to 3 (neutral) - user can update later
- **peer_reviewed**: Set to true for journal articles

#### File Paths (derive from input)
- **file_path_pdf**: Same path as markdown file but with .pdf extension
- **file_path_markdown**: The input markdown file path (use absolute path)

#### Content Fields

1. **abstract** (verbatim)
   - Copy the abstract exactly as it appears in the paper
   - Do not summarize or modify
   - Must be under 1000 words

2. **question** (600-1000 words if source >1000 words)
   - Extract or synthesize the research question(s) the paper addresses
   - If the source content exceeds 1000 words, summarize to 600-1000 words
   - Preserve the core research questions and hypotheses

3. **method** (600-1000 words if source >1000 words)
   - Extract the methodology section
   - If the source content exceeds 1000 words, summarize to 600-1000 words
   - Include: research design, sample/participants, data collection, analysis approach

4. **gaps** (600-1000 words if source >1000 words)
   - Extract identified limitations and gaps from the paper
   - Include: stated limitations, future research directions, acknowledged constraints
   - If the source content exceeds 1000 words, summarize to 600-1000 words

5. **results** (600-1000 words if source >1000 words)
   - Extract key findings and results
   - If the source content exceeds 1000 words, summarize to 600-1000 words
   - Preserve statistical findings, key metrics, and main outcomes

6. **interpretation** (600-1000 words if source >1000 words)
   - Extract the discussion/interpretation of results
   - If the source content exceeds 1000 words, summarize to 600-1000 words
   - Include: meaning of findings, theoretical implications, practical implications

7. **claims** (600-1000 words if source >1000 words)
   - Extract key verifiable claims as a bullet list
   - If the source content exceeds 1000 words, summarize to 600-1000 words
   - Format as markdown bullet points
   - Each claim should be specific and verifiable

8. **quotes** (minimum 10 entries, 50-200 words each)
   - Extract at least 10 verbatim quotes from the paper
   - Each quote must be 50-200 words
   - Include page number for each quote
   - Select quotes that:
     - Support key claims
     - Define important concepts
     - State significant findings
     - Provide methodological details
     - Can be used for citation verification

9. **full_text** (AUTO-POPULATED - do not include in JSON)
   - The CLI automatically reads the entire markdown file from `file_path_markdown`
   - No need to include this field in the JSON
   - Used for BM25 full-text search indexing

### JSON Output Schema

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
  "abstract": "The verbatim abstract from the paper...",
  "question": "The research question(s) addressed by this paper...",
  "method": "The methodology used in this research...",
  "gaps": "Identified limitations and gaps...",
  "results": "Key findings and results...",
  "interpretation": "Discussion and interpretation of results...",
  "claims": "- Claim 1: Specific verifiable claim\n- Claim 2: Another claim\n- ...",
  "quotes": [
    {"text": "Verbatim quote from the paper that is between 50-200 words...", "page": 102},
    {"text": "Another significant quote...", "page": 105},
    {"text": "Quote supporting a key claim...", "page": 108},
    {"text": "Quote defining an important concept...", "page": 110},
    {"text": "Quote stating a significant finding...", "page": 112},
    {"text": "Quote with methodological detail...", "page": 103},
    {"text": "Quote for citation verification...", "page": 115},
    {"text": "Additional relevant quote...", "page": 118},
    {"text": "Quote supporting interpretation...", "page": 120},
    {"text": "Final key quote from conclusions...", "page": 122}
  ]
}
```

**Note:** The `full_text` field is automatically populated by the CLI from `file_path_markdown` during import. Do not include it in the JSON.

### Validation Checklist

Before outputting the JSON, verify:

- [ ] `id` follows format: `<surname><year>[a-z]?` (lowercase)
- [ ] `author` has minimum 2 characters
- [ ] `title` has minimum 5 characters
- [ ] `year` is 4-digit year between 1900 and current year + 1
- [ ] `journal`, `volume`, `number`, `issue`, `pages`, `publisher` have minimum 1 character
- [ ] `doi` has minimum 2 characters
- [ ] `url` starts with http:// or https:// (or is null)
- [ ] `file_path_pdf` and `file_path_markdown` are absolute paths starting with `/` or `~`
- [ ] `keywords` is not empty
- [ ] `rating` is between 1-5
- [ ] `abstract`, `question`, `method`, `gaps`, `results`, `interpretation`, `claims` are each under 1000 words
- [ ] `quotes` has at least 10 entries, each with `text` (50-200 words) and `page` (positive integer)
- [ ] `full_text` is NOT included (auto-populated from `file_path_markdown`)

### Example Workflow

1. User provides: `/Users/dennis/papers/ashford2012.md`
2. Claude reads the markdown file
3. Claude extracts metadata from the paper header
4. Claude processes each content field according to the rules above
5. Claude generates JSON with:
   - `file_path_markdown`: `/Users/dennis/papers/ashford2012.md`
   - `file_path_pdf`: `/Users/dennis/papers/ashford2012.pdf`
6. Claude saves JSON to `/Users/dennis/papers/ashford2012.json`
7. User can then run: `paper-index-tool create-from-json /Users/dennis/papers/ashford2012.json`

### Word Count Guidelines

| Field | Target Length | Action if Source > 1000 words |
|-------|---------------|------------------------------|
| abstract | Verbatim | Copy exactly (should be <1000) |
| question | 600-1000 | Summarize preserving core questions |
| method | 600-1000 | Summarize preserving key methodology |
| gaps | 600-1000 | Summarize preserving limitations |
| results | 600-1000 | Summarize preserving key findings |
| interpretation | 600-1000 | Summarize preserving implications |
| claims | 600-1000 | Summarize as bullet list |
| quotes | 10+ entries | Each 50-200 words with page ref |
| full_text | N/A | Auto-populated from file_path_markdown |

### Notes

- Always use absolute file paths
- Preserve academic rigor and accuracy in summaries
- When summarizing, prioritize:
  1. Core findings and conclusions
  2. Methodological details that affect interpretation
  3. Specific data points and statistics
  4. Theoretical contributions
- For quotes, select diverse passages covering different sections of the paper
- If metadata is unclear, make reasonable inferences and note uncertainty in a comment
