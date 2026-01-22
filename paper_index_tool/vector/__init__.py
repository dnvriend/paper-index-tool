"""Vector search module for paper-index-tool.

This module provides semantic search capabilities using AWS Bedrock embeddings
and FAISS vector index. It enables natural language queries that match on
meaning rather than keywords.

Classes:
    VectorSearcher: Semantic search across papers, books, and media.
    BedrockEmbeddings: AWS Bedrock embedding client.
    EmbeddingStats: Statistics from embedding generation (tokens, cost).
    TextChunker: Text chunking with page/section tracking.
    Chunk: A text chunk with metadata.

Exceptions:
    VectorSearchError: Base exception for vector search operations.
    EmbeddingError: Failed to generate embeddings.
    IndexNotFoundError: Vector index not found.
    AWSCredentialsError: AWS credentials not configured.

Functions:
    ensure_vector_index: Ensure vector index exists.

Note: This module requires the 'vector' optional dependencies:
    pip install paper-index-tool[vector]
    # or
    uv sync --extra vector
"""

from paper_index_tool.vector.chunking import (
    CharacterLimitChunker,
    Chunk,
    ChunkerPipeline,
    TextChunker,
)
from paper_index_tool.vector.embeddings import (
    DEFAULT_MODEL,
    DEFAULT_REGION,
    EMBEDDING_MODELS,
    BedrockEmbeddings,
    EmbeddingModelConfig,
    EmbeddingStats,
    get_model_config,
    validate_dimensions,
)
from paper_index_tool.vector.errors import (
    AWSCredentialsError,
    ChunkingError,
    EmbeddingError,
    IndexNotFoundError,
    ModelMismatchError,
    NamedIndexNotFoundError,
    VectorSearchError,
)
from paper_index_tool.vector.registry import (
    VectorIndexRegistry,
    remove_entry_from_all_indices,
    update_all_indices_with_entry,
)
from paper_index_tool.vector.search import VectorSearcher

__all__ = [
    # Classes
    "BedrockEmbeddings",
    "CharacterLimitChunker",
    "Chunk",
    "ChunkerPipeline",
    "EmbeddingModelConfig",
    "EmbeddingStats",
    "TextChunker",
    "VectorIndexRegistry",
    "VectorSearcher",
    # Constants
    "DEFAULT_MODEL",
    "DEFAULT_REGION",
    "EMBEDDING_MODELS",
    # Functions
    "get_model_config",
    "remove_entry_from_all_indices",
    "update_all_indices_with_entry",
    "validate_dimensions",
    # Exceptions
    "AWSCredentialsError",
    "ChunkingError",
    "EmbeddingError",
    "IndexNotFoundError",
    "ModelMismatchError",
    "NamedIndexNotFoundError",
    "VectorSearchError",
]
