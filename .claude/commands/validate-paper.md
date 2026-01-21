# Validate Paper Entry

Validate and interact with paper entries using `paper-index-tool`.

## CLI Reference

### CRUD Operations

```bash
# Create
paper-index-tool paper create <id> [--field value...]
paper-index-tool create-from-json <filename>

# Read
paper-index-tool paper show <id> [--format json]
paper-index-tool paper list [--format json] [--count]

# Update
paper-index-tool paper update <id> [--field value...]
paper-index-tool update-from-json <filename>

# Delete
paper-index-tool paper delete <id> [--force]
```

### Field Queries (Quick Access)

```bash
paper-index-tool paper abstract <id>      # Paper abstract
paper-index-tool paper question <id>      # Research question
paper-index-tool paper method <id>        # Methodology
paper-index-tool paper gaps <id>          # Limitations/gaps
paper-index-tool paper results <id>       # Key findings
paper-index-tool paper claims <id>        # Verifiable claims
paper-index-tool paper quotes <id>        # Quotes with page refs
paper-index-tool paper file-path-pdf <id> # PDF file path
paper-index-tool paper file-path-md <id>  # Markdown file path
```

### Bibtex Export

```bash
paper-index-tool paper bibtex <id>        # Generate bibtex entry
paper-index-tool book bibtex <id>         # Generate book bibtex
```

### Statistics

```bash
paper-index-tool stats                    # All statistics
paper-index-tool stats --format json      # JSON format
```

### BM25 Search

```bash
# Search single entry
paper-index-tool query <id> "search terms"
paper-index-tool paper query <id> "search terms" [--fragments]
paper-index-tool book query <id> "search terms" [--fragments]

# Search all entries
paper-index-tool query --all "search terms" [--fragments] [-C <context>] [-n <num>]
```

### Import/Export

```bash
# Export all data
paper-index-tool export <filename>

# Import data
paper-index-tool import <filename> [--replace|--merge] [--dry-run]

# Rebuild search index
paper-index-tool reindex
```

## Validation Workflow

1. **Check entry exists**:
   ```bash
   paper-index-tool paper show <id>
   ```

2. **Validate specific fields**:
   ```bash
   paper-index-tool paper claims <id>
   paper-index-tool paper method <id>
   ```

3. **Search for specific content**:
   ```bash
   paper-index-tool paper query <id> "keyword"
   ```

4. **Export bibtex for citation**:
   ```bash
   paper-index-tool paper bibtex <id>
   ```

## Common Use Cases

### Citation Verification

```bash
# Get claims for a paper
paper-index-tool paper claims ashford2012

# Get quotes with page references
paper-index-tool paper quotes ashford2012

# Search for specific finding
paper-index-tool paper query ashford2012 "identity work"
```

### Literature Review

```bash
# Search all papers for a topic
paper-index-tool query "leadership development" --all --fragments

# Get methodology comparison
paper-index-tool paper method paper1
paper-index-tool paper method paper2

# View statistics
paper-index-tool stats
```

### Reference Management

```bash
# Export bibtex for all papers
for id in $(paper-index-tool paper list --format json | jq -r '.[].id'); do
  paper-index-tool paper bibtex $id
done

# Backup all data
paper-index-tool export papers-backup.json
```
