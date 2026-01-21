# Enhanced Citation Validation System

## Problem Statement

Current system can find *that* a fact exists in a paper, but not *where* (page number) for arbitrary searches. Only the 10 pre-selected quotes have page references.

## Use Case

Enable Claude Code to automatically validate claims in user-written papers against indexed sources:
1. Extract claims with citations from user's draft
2. Search indexed papers for supporting evidence
3. Return validation results with exact page references
4. Propose corrections for unsupported or inaccurate claims

## Proposed Solutions (Progressive Complexity)

### Option 1: Page-Marked Full Text (LOW effort)

**Concept:** Embed page markers in the markdown source files.

```markdown
[PAGE:208]
Due to the COVID-19 crisis, managers and employees...

[PAGE:209]
Research on neuropsychology in response to threat...
```

**Implementation:**
1. Update markdown files with `[PAGE:N]` markers during PDF conversion
2. Modify search to extract page from surrounding context
3. New command: `paper validate <id> "claim text"` returns fragment + page

**Pros:** Simple, no new dependencies, works with existing BM25
**Cons:** Requires re-processing markdown files with page markers

### Option 2: Chunked Index with Page Metadata (MEDIUM effort)

**Concept:** Split papers into searchable chunks with page tracking.

```python
# New model
class PaperChunk(BaseModel):
    paper_id: str
    chunk_id: int
    text: str           # ~300-500 words
    page_start: int
    page_end: int
    section: str | None # "Method", "Results", etc.
```

**Implementation:**
1. Add `chunks` field to Paper model (list of PaperChunk)
2. Parse full_text into chunks, detect page boundaries
3. Index chunks separately for granular search
4. Query returns: chunk text + page range + section

**New command:**
```bash
paper-index-tool cite stoker2022 "managers delegate less during crisis"
# Returns:
# [p.213-214] "employees of lower-level managers even report a
#              significant decrease in delegation" (Results section)
# Confidence: 0.87
```

**Pros:** Precise page references, section awareness
**Cons:** More storage, requires chunking logic

### Option 3: Vector Search via Bedrock (HIGH effort, HIGH accuracy)

**Concept:** Semantic search using embeddings for meaning-based matching.

```
Your claim: "WFH reduces manager control"
    ↓ embed via Bedrock
Query vector → search chunk vectors
    ↓
Match: "managers cannot execute their role in the same way"
       (semantic match, not keyword)
```

**Implementation:**
1. Chunk papers (~300 words per chunk)
2. Embed chunks via `amazon.titan-embed-text-v2`
3. Store vectors (local FAISS or Bedrock Knowledge Base)
4. Query: embed claim → cosine similarity → top-k chunks

**New command:**
```bash
paper-index-tool validate stoker2022 "thuiswerken vermindert controle"
# Works even in Dutch! Semantic matching.
```

**Pros:**
- Catches paraphrases and translations
- Best for validating your own writing (different wording than source)
- Handles "the paper claims X" style validation

**Cons:**
- API cost (~$0.0001 per 1000 tokens)
- Requires vector storage
- More complex infrastructure

### Option 4: Hybrid BM25 + Vector (HIGHEST accuracy)

**Concept:** Use both approaches, combine scores.

```
Query → BM25 search (keyword matches)
     → Vector search (semantic matches)
     → Merge & rank results
     → Return with confidence score
```

**Validation output:**
```
Claim: "@stoker2022 toont aan dat managers meer delegeren"

VALIDATION RESULT: PARTIALLY SUPPORTED

BM25 Match [p.213]:
  "Managers also perceived an increase in their level of
   delegation (M = 0.26, SD = 1.00)"
  → Managers PERCEIVE they delegate more ✓

Vector Match [p.213]:
  "Employees perceived no significant change in delegation"
  → But employees don't agree ⚠️

Suggested revision:
  "@stoker2022 toont aan dat managers DENKEN dat ze meer
   delegeren, maar medewerkers ervaren dit niet"
```

## Recommended Implementation Path

**Phase 1 (Quick Win):** Option 1 - Page markers
- Modify PDF→MD conversion to include `[PAGE:N]`
- Update search to show page context
- Minimal code changes

**Phase 2 (Full Solution):** Option 2 + Option 3
- Chunk storage with page metadata
- Add optional vector search (`--semantic` flag)
- Hybrid validation command

## Cost Estimate (Vector Search)

| Item | Cost |
|------|------|
| Embed 50 papers × 10K words | ~$0.50 one-time |
| Per query | negligible |
| Monthly (heavy use) | < $5 |

## New CLI Commands (Proposed)

```bash
# Validate a specific claim against a paper
paper-index-tool validate <id> "your claim text" [--semantic]

# Bulk validate a markdown file with citations
paper-index-tool validate-doc mydraft.md --output report.md

# Show citation with page reference
paper-index-tool cite <id> "search terms"
# → Returns: "[stoker2022, p.213] exact quote..."

# Re-index with page markers
paper-index-tool reindex --with-pages
```

## Data Model Changes

### Option 2: Add chunks to Paper model

```python
class PaperChunk(BaseModel):
    """A searchable chunk of paper content with page reference."""
    chunk_id: int
    text: str
    page_start: int
    page_end: int
    section: str | None = None

class Paper(BaseModel):
    # ... existing fields ...
    chunks: list[PaperChunk] = []
```

### Option 3: Vector storage

```python
class ChunkEmbedding(BaseModel):
    """Vector embedding for a paper chunk."""
    paper_id: str
    chunk_id: int
    embedding: list[float]  # 1024-dim for Titan v2
    text: str
    page: int
```

Storage options:
- Local: FAISS index file (`~/.config/paper-index-tool/vectors.faiss`)
- Cloud: Bedrock Knowledge Base (managed, but more complex)

## Success Criteria

1. Given a claim and paper ID, return supporting text with page number
2. Detect when a claim is NOT supported by the cited paper
3. Handle paraphrased claims (semantic search)
4. Process a full document and flag all citation issues
5. Suggest corrections with accurate quotes and page references

## Dependencies

### Option 1-2 (BM25 only)
- No new dependencies

### Option 3-4 (Vector search)
```toml
[project.optional-dependencies]
vector = [
    "boto3>=1.34",
    "faiss-cpu>=1.7",
]
```

## Related

- [feature.md](./feature.md) - Main feature specification
- [generate-entries-prompt.md](./generate-entries-prompt.md) - Paper entry generation
