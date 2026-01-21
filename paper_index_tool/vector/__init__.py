"""Vector search module for paper-index-tool.

This module provides semantic search capabilities using AWS Bedrock embeddings
and FAISS vector index. It enables natural language queries that match on
meaning rather than keywords.

Classes:
    VectorSearcher: Semantic search across papers, books, and media.
    BedrockEmbeddings: AWS Bedrock embedding client.
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

from paper_index_tool.vector.chunking import Chunk, TextChunker
from paper_index_tool.vector.embeddings import BedrockEmbeddings
from paper_index_tool.vector.errors import (
    AWSCredentialsError,
    EmbeddingError,
    IndexNotFoundError,
    VectorSearchError,
)
from paper_index_tool.vector.search import VectorSearcher

__all__ = [
    # Classes
    "BedrockEmbeddings",
    "Chunk",
    "TextChunker",
    "VectorSearcher",
    # Exceptions
    "AWSCredentialsError",
    "EmbeddingError",
    "IndexNotFoundError",
    "VectorSearchError",
]
