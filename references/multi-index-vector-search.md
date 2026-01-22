# Multi-Index Vector Search

## Overview

Support for multiple named vector indices with configurable embedding models and dimensions. Each index uses its own model configuration and can be independently managed.

## Supported Embedding Models

| CLI Name | Model ID | Dimensions | Configurable |
|----------|----------|------------|--------------|
| titan-v1 | amazon.titan-embed-text-v1 | 1536 | No (fixed) |
| titan-v2 | amazon.titan-embed-text-v2:0 | 1024 | No (fixed) |
| cohere-en | cohere.embed-english-v3 | 1024 | No (fixed) |
| cohere-multi | cohere.embed-multilingual-v3 | 1024 | No (fixed) |
| nova | amazon.nova-embed-text-v1:0 | 256/512/1024 | Yes |

## CLI Commands

### Create Index

```bash
# Create with default titan-v2 model
paper-index-tool vector create my-index

# Create with specific model
paper-index-tool vector create nova-1024 --model nova --dimensions 1024
paper-index-tool vector create titan-default --model titan-v2
paper-index-tool vector create cohere-search --model cohere-en

# With custom chunking
paper-index-tool vector create my-index --model nova --dimensions 512 \
    --chunk-size 400 --chunk-overlap 75
```

### List Indices

```bash
paper-index-tool vector list
paper-index-tool vector list --format json
```

Output:
```
Vector Indices (2):

  nova-1024 (default)
    Model: nova (amazon.nova-embed-text-v1:0)
    Dimensions: 1024
    Chunks: 2450
    Cost: $0.024500

  titan-v2
    Model: titan-v2 (amazon.titan-embed-text-v2:0)
    Dimensions: 1024
    Chunks: 2450
    Cost: $0.049000
```

### Show Index Info

```bash
paper-index-tool vector info nova-1024
paper-index-tool vector info nova-1024 --format json
```

Output:
```
Index: nova-1024 (default)
  Model: nova (amazon.nova-embed-text-v1:0)
  Dimensions: 1024
  Chunk size: 300 words
  Chunk overlap: 50 words
  Chunks: 2450
  Tokens processed: 245000
  Estimated cost: $0.024500
  Created: 2024-01-22 14:30:00
  Updated: 2024-01-22 15:45:00
```

### Set Default Index

```bash
# Show current default
paper-index-tool vector default

# Set default
paper-index-tool vector default nova-1024

# Clear default
paper-index-tool vector default --clear
```

### Rebuild Index

```bash
paper-index-tool vector rebuild nova-1024
```

### Delete Index

```bash
paper-index-tool vector delete nova-1024
paper-index-tool vector delete nova-1024 --force
```

## Semantic Search

### Using Default Index

```bash
# Uses default index (from settings)
paper-index-tool query "How do leaders develop?" --all --semantic
```

### Using Specific Index

```bash
# Use specific named index
paper-index-tool query "leadership development" --all --semantic --index nova-1024
paper-index-tool query "leadership development" --all -s -i titan-v2
```

### Search Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--semantic` | `-s` | Enable semantic search |
| `--index` | `-i` | Specify named vector index |
| `--fragments` | | Show matching text fragments |
| `-C <n>` | | Context lines around match |
| `-n <n>` | | Number of results |

## Storage Structure

```
~/.config/paper-index-tool/
├── papers.json
├── books.json
├── media.json
├── settings.json                    # Default index setting
├── bm25s/
└── vectors/
    ├── indices.json                 # Registry of all indices
    └── <index-name>/                # e.g., "nova-1024/"
        ├── index.faiss              # FAISS vector index
        ├── chunks.json              # Chunk metadata
        └── metadata.json            # Index configuration
```

## Data Models

### VectorIndexMetadata

```python
class VectorIndexMetadata(BaseModel):
    name: str                         # Index name
    embedding_model: str              # Model ID
    dimensions: int                   # Vector dimensions
    chunk_size: int = 300             # Words per chunk
    chunk_overlap: int = 50           # Overlap between chunks
    chunk_count: int = 0              # Total chunks
    total_tokens: int = 0             # Tokens processed
    estimated_cost_usd: float = 0.0   # Embedding cost
    created_at: datetime
    updated_at: datetime
```

### Settings

```python
class Settings(BaseModel):
    default_vector_index: str | None = None
```

## Cost Estimation

| Model | Price per 1K tokens | 50 papers (~600K tokens) |
|-------|---------------------|--------------------------|
| titan-v1 | $0.0001 | $0.06 |
| titan-v2 | $0.00002 | $0.012 |
| cohere-en | $0.0001 | $0.06 |
| cohere-multi | $0.0001 | $0.06 |
| nova | $0.00001 | $0.006 |

## Programmatic Usage

### Update All Indices When Creating Entry

```python
from paper_index_tool.vector import update_all_indices_with_entry

# Called after creating a paper/book/media
update_all_indices_with_entry(
    entry_id="ashford2012",
    entry_type="paper",
    searchable_text=paper.get_searchable_text(),
)
```

### Remove Entry from All Indices

```python
from paper_index_tool.vector import remove_entry_from_all_indices

# Called before/after deleting a paper/book/media
remove_entry_from_all_indices(entry_id="ashford2012")
```

### Add Single Entry to Index

```python
from paper_index_tool.vector import VectorIndexRegistry

registry = VectorIndexRegistry()
stats = registry.add_entry_to_index(
    name="nova-1024",
    entry_id="new-paper",
    entry_type="paper",
    searchable_text="...",
)
```

## AWS Requirements

### Credentials

Uses boto3 credential chain:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS profile (`AWS_PROFILE`)
3. IAM role (if running on AWS)

### IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "bedrock:InvokeModel",
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1",
                "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
                "arn:aws:bedrock:*::foundation-model/amazon.nova-embed-text-v1:0",
                "arn:aws:bedrock:*::foundation-model/cohere.embed-english-v3",
                "arn:aws:bedrock:*::foundation-model/cohere.embed-multilingual-v3"
            ]
        }
    ]
}
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `NamedIndexNotFoundError` | Index doesn't exist | Create with `vector create` |
| `ModelMismatchError` | Query model differs from index | Use same model or specify `--index` |
| `AWSCredentialsError` | Missing AWS credentials | Configure AWS profile or env vars |
| `IndexNotFoundError` | Legacy index not built | Run `reindex --vectors` |

## Migration from Legacy Index

If you have an existing legacy vector index (from `reindex --vectors`), you can continue using it. The legacy index is used when no named index is specified and no default is set.

To migrate to named indices:

```bash
# Create a new named index
paper-index-tool vector create my-index --model titan-v2

# Set as default
paper-index-tool vector default my-index

# Now semantic search uses the named index
paper-index-tool query "..." --all --semantic
```

## Related Documentation

- [Vector Search Feature](./vector-search-feature.md) - Original semantic search design
- [Manual](./manual.md) - General usage guide
