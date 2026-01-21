# paper-index-tool

## Problem
When I search for a paper, I repeatately have the same questions about the paper,
- what is the abstract
- what is the question it tries to answer
- what are the results
- what is the method followed
- what are the gaps
- what is the quality of the paper
- what are some of the details
- what papers is it based on
- what is the content exactly
- who are the authors
- where was it published
- when was it published

Some of these problems bibtex address but also that is a problem:

- bibtex entries stack up in the same file, multiple entries of the same paper
- multiple entries of the same paper with different names or details
- where is the paper located on disk
- do I have pdf/markdown/html content of the paper, pdf is nice but markdown is better for AI processing
- I don't know where the source comes from or if the source comes from AI hallucinations
  
To answer these questions I have to
- have a bibtex tool that deduplicates, sort and orders, 
- AI processes full text again and again to answer the question
- AI reprocessing as it is stochastic, results in different answers each and every time
- AI (re)processsing can cause hallucinations depending on the generation
- AI due to stochastic by nature; there is no "one perfect generation"

Other problems that I did not mention here but fall in the same category

## Vision

Also I am going to write a lot-of-papers and will have more and more papers locally. I now cannot find them, or don't remember where the papers are stored, so I'm getting really confused. I need a good source of truth that I can query eg like:

paper-index-tool list: returns the list of papers that we have indexed eg:

[ashford2012]: <title> <authors> <year>
 <1-2 sentence abstract>
[badura2018]: <title> <authors> <year>
 <1-2 sentence abstract>

---

paper-index-tool abstract ashford2012: returns the abstract
paper-index-tool question ashford2012: returns the question
paper-index-tool method ashford2012: returns the method
paper-index-tool gaps ashford2012: returns the gaps
paper-index-tool results ashford2012: returns the results
paper-index-tool <command> <paper>

---

paper-index-tool query ashford2012 "your search terms here": returns the bm25 result in the paper eg:
index query obsidian "foo" --fragments -C 1 -n 1
[1] full path to the paper (score: 5.4618)

    Fragment 1 (lines 16-18):
    ----------------------------------------
    // setup:
    exports.foo = deprecate(foo, 'foo() is deprecated, use bar() instead');


    Fragment 2 (lines 20-25):
    ----------------------------------------
    // users see:
    foo();
    // foo() is deprecated, use bar() instead
    foo();
    foo();

paper-index-tool query "your search terms here" --all --fragments -C 1 -n 1: searches through all papers eg:
[1] full path to the paper (score: 5.4618)

    Fragment 1 (lines 16-18):
    ----------------------------------------
    // setup:
    exports.foo = deprecate(foo, 'foo() is deprecated, use bar() instead');


    Fragment 2 (lines 20-25):
    ----------------------------------------
    // users see:
    foo();
    // foo() is deprecated, use bar() instead
    foo();
    foo();

---

paper-index-tool bibtex ashford2012: prints the bibtext on the CLI that I can copy/paste including the full path to the PDF

---

paper-index-tool create ashford2012: creates an entry must accept the bibtext fields as flags eg:

paper-index-tool create ashford2012 --author "" --publisher "" --year "" and all the objects too like --abstract, --gaps, --method, --results etc, all optional

paper-index-tool update ashford2012 --gaps "" --results "" will overwrite the fields that are set, leaves the other fields, all create fields are supported

paper-index-tool delete ashford2012: deletes a paper

---

## What the tool can help with
A quick way, also for the AI to have grounding information in order to quickly check the quality of a paper or part of a paper that I write and make sure the content is actually grounded in truth; this is essential

## Solution
I need a database that is the source of truth for:
- finding where the PDFs/md/html is located
- finding the details of a paper:
  - the abstract
  - the question it tries to answer
  - the method
  - the gaps
  - the results
  - the interpretation of the results
  - what are the gaps
  - what is the quality of the paper
  - what are some of the details
  - what papers is it based on
  - what is the content exactly
  - who are the authors
  - where was it published
  - when was it published
  - full text of the report
- search on metadata of the paper (author, year, basically the bibtex fields, title, etc)
- search on content in the abstract, question, method, gaps, results, interpretation, etc
- search on the text of the report

## Possible implementation
I see multiple objects/things:

1. the title as a thing
These are basically the bibtex metadata of the paper, all the fields, but *also* inclusing the full path to the source; JabRef has a standard for this

2. The full text of the paper in markdown
Papers need to be converted to markdown, most that I have are already in markdown, this text needs to be searched using bm25 and vector search using AWS Bedrock vector embedding models; the best they have so we have similarity search and term/keyword search using bm25. 

3. We need to define objects when we break down a paper, like abstract, question, method, gaps, results, interpretation, quality (peer reviewed etc), authors, etc. These objects need to be generated by an LLM like claude code. If we have a CLI that claude code can call creating these objects from an interpretation of a paper, then we do not have to code this; claude code can just read the paper markdown and do a create if we have the paper ID, this nicely goes into the next, how do we identify a paper

4. We need to identify a paper uniquely. I like the <name><year><a-z> identity eg. ashford2012 and for duplicates ashford2012a, ashford2012b, ashford2012c etc

## MVP Specification (Refined)

Based on interview refinement:

### Storage

- **Location**: `~/.config/paper-index-tool/`
- **Engine**: bm25s library (same approach as bm25-index-tool)
- **Structure**:
  - `papers.json` - Paper metadata registry
  - `bm25s/` - BM25 search index for all searchable content

### Paper ID

- Manual input (e.g., `ashford2012`, `badura2018a`)
- Format: `<surname><year>[a-z]` for duplicates
- Error if ID already exists on create

### Data Model for Papers

**Bibtex Fields (Extended)**:

| Field | Type | Description | Validation | Mandatory |
|-------|------|-------------|----------- | --------- |
| `id` | string | Unique paper ID (e.g., ashford2012) | regex validation | yes |
| `author` | string | Author(s) | length=2 | yes |
| `title` | string | Paper title | length=5 | yes |
| `year` | int | Publication year | numbers regex | yes |
| `journal` | string | Journal name | length=5 | yes |
| `volume` | string | Volume number | length=2 | yes |
| `number` | string | Volume number | lenght=2 | yes |
| `issue` | string | Issue number | length=2 | yes |
| `pages` | string | Page range | length=2 | yes |
| `publisher` | string | Publisher | length=2 | yes |
| `doi` | string | DOI | length=2 | yes |
| `url` | string | URL | http regex | no |
| `file_path_pdf` | string | Full path to PDF file | file regex | yes |
| `file_path_markdown` | string | Full path to markdown file | file regex | yes |
| `keywords` | string | Comma-separated keywords | list regex | yes |
| `rating` | int | 1-5 quality rating | number | yes |
| `peer-reviewed` | bool | regex | yes | 

**Paper Content Fields (Free-form text, all searchable)**:

| Field | Description | Validation | 
|-------|-------------| ---------- |
| `abstract` | Paper abstract | length=400 words (wc -w) or similar |
| `question` | Research question the paper tries to answer | length=400 words (wc -w) or similar  |
| `method` | Research method/methodology | length=400 words (wc -w) or similar |
| `gaps` | Identified gaps or limitations | length=400 words (wc -w) or similar |
| `results` | Key results/findings | length=400 words (wc -w) or similar |
| `interpretation` | Interpretation of results | length=400 words (wc -w) or similar |
| `claims` | Key verifiable claims/findings (bullet points) | length=400 words (wc -w) or similar |
| `quotes` | Verbatim quotes with page refs (JSON array: `[{"text": "...", "page": 5}]`) | length>=10 entries in the array |
| `full_text` | Full paper content in markdown (AUTO-POPULATED from `file_path_markdown`) | length >= 1000 words |

**Note:** The `full_text` field is automatically populated by reading the content from `file_path_markdown` during `create-from-json` or `update-from-json`. This enables BM25 full-text search without requiring the content to be duplicated in the JSON.

### Data Model for Books

**Bibtex Fields (Extended)**:

| Field | Type | Description | Validation | Mandatory |
|-------|------|-------------|----------- | --------- |
| `id` | string | Unique paper ID (e.g., ashford2012) | regex validation | yes |
| `author` | string | Author(s) | length=2 | yes |
| `title` | string | Paper title | length=5 | yes |
| `year` | int | Publication year | numbers regex | yes |
| `pages` | string | Page range | length=2 | yes |
| `publisher` | string | Publisher | length=2 | yes |
| `url` | string | URL | http regex | no |
| `isbn` | string | ISBN | length=2 | no |
| `chapter` | string | The chapter | length=2 | yes |
| `file_path_pdf` | string | Full path to PDF file | file regex | yes |
| `file_path_markdown` | string | Full path to markdown file | file regex | yes |
| `keywords` | string | Comma-separated keywords | list regex | yes |

**Book Content Fields (Free-form text, all searchable)**:

| Field | Description | Validation | 
|-------|-------------| ---------- |
| `abstract` | Paper abstract | length=400 words (wc -w) or similar |
| `question` | Research question the paper tries to answer | length=400 words (wc -w) or similar  |
| `method` | Research method/methodology | length=400 words (wc -w) or similar |
| `gaps` | Identified gaps or limitations | length=400 words (wc -w) or similar |
| `results` | Key results/findings | length=400 words (wc -w) or similar |
| `interpretation` | Interpretation of results | length=400 words (wc -w) or similar |
| `claims` | Key verifiable claims/findings (bullet points) | length=400 words (wc -w) or similar |
| `quotes` | Verbatim quotes with page refs (JSON array: `[{"text": "...", "page": 5}]`) | length>=10 entries in the array |
| `full_text` | Full book/chapter content in markdown (AUTO-POPULATED from `file_path_markdown`) | length >= 1000 words |

**Note:** The `full_text` field is automatically populated by reading the content from `file_path_markdown` during `create-from-json` or `update-from-json`. This enables BM25 full-text search without requiring the content to be duplicated in the JSON.

### CLI Commands

```bash
# CRUD Operations
paper-index-tool paper create <id> [--field value...]   # Create paper entry
paper-index-tool paper show <id>                        # Show all paper details
paper-index-tool paper update <id> [--field value...]   # Update paper entry specific fields
paper-index-tool paper delete <id>                      # Delete paper

# stats
paper-index-tool stats                            # Shows statistics, total number of papers, from which author, which keywords breakdown in numbers in table

# Json commands
paper-index-tool create-from-json <filename>      # Create entry from json file depending on the model a paper or a book
paper-index-tool update-from-json <filename>      # Update entry from json file depending on the model a paper or a book


# Field Queries (quick access)
paper-index-tool paper abstract <id>                    # Show abstract only
paper-index-tool paper question <id>                    # Show research question
paper-index-tool paper method <id>                      # Show method
paper-index-tool paper gaps <id>                        # Show gaps
paper-index-tool paper results <id>                     # Show results
paper-index-tool paper claims <id>                      # Show key claims/findings
paper-index-tool paper quotes <id>                      # Show stored quotes with page refs
paper-index-tool paper file-path-pdf <id>               # Show the PDF file path
paper-index-tool paper file-path-md <id>                # Show the Markdown file path

# Bibtext generation
paper-index-tool paper bibtex <id>                      # Generates paper bibtext with all fields
paper-index-tool book bibtex <id>                       # Generates book bibtext with all fields

# Exports all data to json file
paper-index-tool export <filename>                # Export all papers to a json file

# Flushes current bm25 index and imports all data from json file
paper-index-tool import <filename>                # Flushes bm25 indexes and imports all data from json file

# BM25 Search
paper-index-tool query <id> "search terms"        # Search within single paper
paper-index-tool query --all "search terms"       # Search across all papers
  --fragments                                     # Show matching fragments
  -C <n>                                          # Context lines around match
  -n <n>                                          # Number of results
```

### Output Format

- **Default**: Human-readable (formatted text)
- **Optional**: `--format json` for machine parsing (useful for AI agents)

### Example Usage

```bash
# Create a paper entry (Claude Code would generate this)
paper-index-tool paper create ashford2012 \
  --author "Ashford, S. J., & DeRue, D. S." (mandatory) \
  --title "Developing as a leader" (mandatory) \
  --year 2012 (mandatory) \
  --journal "Organizational Dynamics" \
  --abstract "This paper examines how individuals develop..." (mandatory) \
  --question "How do individuals develop leadership identity?" (mandatory) \
  --method "Qualitative interview study with 50 executives" (mandatory) \
  --file-path "/Users/dennis/papers/ashford2012.md" (mandatory)

# Quick queries
paper-index-tool paper abstract ashford2012
paper-index-tool paper method ashford2012

# Search
paper-index-tool paper query ashford2012 "leadership identity"
paper-index-tool book query ash
paper-index-tool query --all "qualitative research" --fragments -C 2 -n 5

# Export bibtex for citation
paper-index-tool bibtex ashford2012

# Citation validation workflow
# Given text: "@stoker2022wfh toont aan dat managers zichzelf als minder controlerend..."
paper-index-tool claims stoker2022wfh              # Quick check: what does this paper claim?
paper-index-tool query stoker2022wfh "managers controlling delegating"  # Search for specific claim
paper-index-tool quotes stoker2022wfh              # Get verbatim quotes with page numbers
```

### Implementation Approach

Reuse patterns from `/Users/dennisvriend/projects/bm25-index-tool`:
1. **CLI**: Typer-based commands with `-v/-vv/-vvv` verbosity
2. **Storage**: JSON registry + bm25s index files
3. **Search**: bm25s library with stemming and stopword removal
4. **API**: Facade pattern for programmatic access

### Import/Export Feature

Backup and restore the entire paper index to/from a JSON file.

#### Export Command

```bash
paper-index-tool export <output-file>
paper-index-tool export ~/backups/papers-backup.json
paper-index-tool export papers.json --format json  # default, only format supported
```

**Behavior**:
- Exports all papers from `~/.config/paper-index-tool/papers.json`
- Excludes BM25 index data (only paper metadata and content)
- Output is a JSON array of paper objects
- Overwrites output file if exists (or use `--force` flag)

**Output Format**:
```json
{
  "version": "1.0",
  "exported_at": "2026-01-20T20:30:00",
  "paper_count": 42,
  "papers": [
    {
      "id": "ashford2012",
      "author": "Ashford, S. J., & DeRue, D. S.",
      "title": "Developing as a leader",
      "year": 2012,
      ...
    },
    ...
  ],
  "books": [
    {
      "id": "vogelgesang2023",
      "author": "Vogelgesang Lester, Gretchen and Lester, Scott W.",
      "title": "Applied Organizational Behavior and Leadership Development: An Identity Approach",
      "year": 2023,
      ...
    },
    ...
  ]
}
```

#### Import Command

```bash
paper-index-tool import <input-file>
paper-index-tool import ~/backups/papers-backup.json
paper-index-tool import papers.json --merge        # Merge with existing (skip duplicates)
paper-index-tool import papers.json --replace      # Replace entire index (default)
```

**Behavior**:
- Reads JSON file with paper array
- `--replace` (default): Clears existing papers and imports all from file
- `--merge`: Adds papers from file, skips if ID already exists
- `--merge --overwrite`: Adds papers, overwrites if ID exists
- After import: Automatically rebuilds BM25 search index
- Validates paper data against Pydantic model before import

**Options**:
| Option | Description |
|--------|-------------|
| `--replace` | Clear existing index, import all (default) |
| `--merge` | Add to existing, skip duplicates |
| `--overwrite` | With --merge: overwrite existing papers |
| `--dry-run` | Show what would be imported without changes |

**Error Handling**:
- Invalid JSON: Error with line number
- Invalid paper data: Skip paper, report error, continue
- Missing required field (id): Skip paper, report error

#### Use Cases

1. **Backup before changes**:
   ```bash
   paper-index-tool export ~/backups/papers-$(date +%Y%m%d).json
   ```

2. **Restore from backup**:
   ```bash
   paper-index-tool import ~/backups/papers-20260120.json --replace
   ```

3. **Merge papers from colleague**:
   ```bash
   paper-index-tool import colleague-papers.json --merge
   ```

4. **Sync across machines**:
   ```bash
   # On machine A
   paper-index-tool export papers.json
   # Copy to machine B
   paper-index-tool import papers.json --replace
   ```

#### Implementation Notes

- Export reads directly from `papers.json` registry
- Import writes to `papers.json` registry
- After import, call `PaperSearcher.rebuild_index()` to regenerate BM25 index
- BM25 index is NOT included in export (regenerated on import)
- Use Pydantic model validation for imported papers

### Future Enhancements (Post-MVP)

- Vector search via AWS Bedrock embeddings

## Bibtex example

**Paper**

```
@article{adams2012,
  author  = {Adams, Renée B. and Funk, Patricia},
  doi     = {10.1287/mnsc.1110.1452},
  journal = {Management Science},
  number  = {2},
  pages   = {219-235},
  title   = {Beyond the Glass Ceiling: Does Gender Matter?},
  volume  = {58},
  year    = {2012}
}
```

**Book**

```
@book{vogelgesang2023,
  author       = {Vogelgesang Lester, Gretchen and Lester, Scott W.},
  isbn         = {978-1-5443-9606-5},
  publisher    = {SAGE Publications},
  title        = {Applied Organizational Behavior and Leadership Development: An Identity Approach},
  year         = {2023}
}
```

## Implementation

Use /skill-python to read up on how I like to develop python code, SOLID design, Object Oriented, separation of concerns, Agent friendly feedback on error or warning messages so that the agent can take a logical next step, rich validation on fields so that the agent knows why something was not accepted with context, same for the command errors, and program errors, "code-rag" comments in the source code.
 