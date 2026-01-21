# Vector Search Feature (Semantic Query)

## Overview

Extend the existing `query` command with semantic search capabilities using AWS Bedrock embeddings. Same interface as BM25 search, but matches on meaning instead of keywords.

## Key Difference: Keywords vs Semantic

| Aspect | BM25 (default) | Semantic (`--semantic`) |
|--------|----------------|-------------------------|
| Input style | Keywords: `"leadership identity"` | Natural language: `"How do people develop as leaders?"` |
| Matching | Exact term matching | Meaning/intent matching |
| Language | Must match source language | Cross-lingual (NL query → EN paper) |
| Best for | Known terminology lookup | Exploratory questions, paraphrased claims |

## CLI Interface

```bash
# Existing BM25 search (unchanged)
paper-index-tool query "delegation control" --all --fragments -C 2 -n 5

# New: Semantic search (same flags)
paper-index-tool query "Do managers delegate less during remote work?" --all --semantic
paper-index-tool query "Do managers delegate less during remote work?" --all -s

# Short form works too
paper-index-tool query "Thuiswerken vermindert controle" -s --all

# Hybrid: combine both (future)
paper-index-tool query "delegation remote work" --all --hybrid
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--semantic` | `-s` | Use vector search instead of BM25 |
| `--hybrid` | `-h` | Combine BM25 + vector scores (future) |
| `--fragments` | | Show matching text fragments |
| `-C <n>` | | Context lines around match |
| `-n <n>` | | Number of results |

### Output Format

Same as BM25 query output:

```
[1] ashford2012 (score: 0.89)
    Fragment 1 (lines 45-52):
    ----------------------------------------
    Leadership identity develops through a process of
    claiming and granting, where individuals...

[2] stoker2022 (score: 0.76)
    Fragment 1 (lines 208-215):
    ----------------------------------------
    Managers reported feeling less able to monitor
    their team's work when remote...
```

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                      CLI Layer                          │
│  query "..." --semantic --fragments -C 2 -n 5          │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   Search Router                         │
│  - Default: BM25Searcher                               │
│  - --semantic: VectorSearcher                          │
│  - --hybrid: HybridSearcher (future)                   │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌─────────────────┐      ┌─────────────────────┐
│  BM25Searcher   │      │   VectorSearcher    │
│  (existing)     │      │   (new)             │
│                 │      │                     │
│  bm25s index    │      │  Bedrock embed API  │
│                 │      │  FAISS index        │
└─────────────────┘      └─────────────────────┘
```

### Data Flow (Semantic Search)

```
1. Query: "How do leaders develop?"
          │
          ▼
2. Embed query via Bedrock
   amazon.titan-embed-text-v2 → [0.12, -0.34, ...] (1024 dims)
          │
          ▼
3. Search FAISS index
   cosine_similarity(query_vec, chunk_vectors)
          │
          ▼
4. Return top-k chunks with metadata
   [(chunk_text, paper_id, page, score), ...]
          │
          ▼
5. Format output (same as BM25)
```

## Data Models

### PaperChunk

```python
class PaperChunk(BaseModel):
    """A searchable chunk of paper content."""
    paper_id: str
    chunk_index: int
    text: str              # ~300 words
    page_start: int
    page_end: int
    section: str | None    # "Abstract", "Method", "Results", etc.
    line_start: int
    line_end: int
```

### ChunkEmbedding

```python
class ChunkEmbedding(BaseModel):
    """Vector embedding for a chunk."""
    paper_id: str
    chunk_index: int
    embedding: list[float]  # 1024 dimensions (Titan v2)
```

## Storage

| File | Description |
|------|-------------|
| `~/.config/paper-index-tool/chunks.json` | Chunk metadata (text, page refs) |
| `~/.config/paper-index-tool/vectors.faiss` | FAISS vector index |
| `~/.config/paper-index-tool/chunk_map.json` | chunk_id → (paper_id, chunk_index) mapping |

## Dependencies

```toml
[project.optional-dependencies]
vector = [
    "boto3>=1.34",
    "faiss-cpu>=1.7",
]
```

Install with: `uv sync --extra vector`

## AWS Bedrock Integration

### Embedding Model

- **Model**: `amazon.titan-embed-text-v2:0`
- **Dimensions**: 1024
- **Max input**: 8192 tokens
- **Cost**: ~$0.0001 per 1000 tokens

### Authentication

Uses standard boto3 credential chain:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM role (if running on AWS)

```bash
# Option 1: Environment
export AWS_PROFILE=my-profile
export AWS_REGION=us-east-1

# Option 2: Explicit in config (future)
paper-index-tool config set aws.profile my-profile
paper-index-tool config set aws.region us-east-1
```

### Required IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"
        }
    ]
}
```

## Chunking Strategy

### Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Chunk size | ~300 words | Balance between context and precision |
| Overlap | 50 words | Prevent losing context at boundaries |
| Min chunk | 100 words | Avoid tiny fragments |

### Page Detection

Chunks track page boundaries via `[PAGE:N]` markers in markdown:

```markdown
[PAGE:208]
Due to the COVID-19 crisis, managers and employees...

[PAGE:209]
Research on neuropsychology shows that...
```

### Section Detection

Detect sections via markdown headers:

```markdown
## Method
...content...

## Results
...content...
```

## Implementation Plan

### Phase 1: Core Infrastructure
- [ ] Add `vector` optional dependencies
- [ ] Create `VectorSearcher` class
- [ ] Implement Bedrock embedding client
- [ ] Implement FAISS index management
- [ ] Add chunking logic with page/section tracking

### Phase 2: CLI Integration
- [ ] Add `--semantic` / `-s` flag to `query` command
- [ ] Add `reindex --vectors` command
- [ ] Update help text with usage examples
- [ ] Add error handling for missing AWS credentials

### Phase 3: Hybrid Search (Future)
- [ ] Add `--hybrid` flag
- [ ] Implement score normalization (BM25 vs cosine)
- [ ] Weighted combination strategy

## Cost Estimation

| Operation | Tokens | Cost |
|-----------|--------|------|
| Index 1 paper (~10K words) | ~12K | ~$0.0012 |
| Index 50 papers | ~600K | ~$0.06 |
| 1 query | ~50 | ~$0.000005 |
| 100 queries/day | ~5K | ~$0.0005/day |

**Monthly estimate (heavy use)**: < $1

## Error Handling

```python
class VectorSearchError(Exception):
    """Base exception for vector search errors."""
    pass

class EmbeddingError(VectorSearchError):
    """Failed to generate embedding via Bedrock."""
    pass

class IndexNotFoundError(VectorSearchError):
    """Vector index not built. Run: paper-index-tool reindex --vectors"""
    pass

class AWSCredentialsError(VectorSearchError):
    """AWS credentials not configured. Set AWS_PROFILE or credentials."""
    pass
```

## Example Session

```bash
# First time: build vector index
$ paper-index-tool reindex --vectors
Chunking 50 papers...
Generating embeddings via Bedrock...
Building FAISS index...
Done. 2,450 chunks indexed.

# Semantic search
$ paper-index-tool query "What happens to leadership when teams work remotely?" --all -s --fragments -n 3

[1] stoker2022 (score: 0.91)
    Section: Results | Pages: 213-214
    ----------------------------------------
    Managers reported that they could not execute their
    role in the same manner as before. Delegation patterns
    shifted significantly...

[2] ashford2012 (score: 0.78)
    Section: Discussion | Pages: 45-46
    ----------------------------------------
    Leadership identity construction requires ongoing
    social interaction, which remote contexts may alter...

[3] bailey2017 (score: 0.71)
    Section: Method | Pages: 12-13
    ----------------------------------------
    We examined how physical distance affects leader-member
    exchange quality...
```

## Related

- [feature.md](./feature.md) - Main feature specification
- [citation-validation-feature.md](./citation-validation-feature.md) - Validation use case (uses this feature)
