"""AWS Bedrock embeddings client for vector search.

This module provides a client for generating text embeddings using
AWS Bedrock's Titan embedding model. Embeddings are used for semantic
search across papers, books, and media.

Classes:
    BedrockEmbeddings: Client for AWS Bedrock text embeddings.

Model:
    amazon.titan-embed-text-v2:0
    - Dimensions: 1024
    - Max input tokens: 8192
    - Languages: English (100+ in preview)
"""

from __future__ import annotations

import json
from typing import Any

from paper_index_tool.logging_config import get_logger
from paper_index_tool.vector.errors import AWSCredentialsError, EmbeddingError

logger = get_logger(__name__)

# Model configuration
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024
MAX_INPUT_TOKENS = 8192


class BedrockEmbeddings:
    """AWS Bedrock embeddings client using Titan v2 model.

    Generates 1024-dimensional embeddings for semantic search.
    Uses boto3 with standard credential chain (env vars, AWS profile, IAM role).

    Attributes:
        model_id: Bedrock model identifier.
        dimensions: Embedding vector dimensions.
        region: AWS region for Bedrock API.

    Example:
        >>> embeddings = BedrockEmbeddings()
        >>> vector = embeddings.embed_text("What is leadership?")
        >>> len(vector)
        1024
    """

    def __init__(self, region: str | None = None) -> None:
        """Initialize Bedrock embeddings client.

        Uses boto3 credential chain: environment variables, AWS profile,
        or IAM role. Region can be specified or defaults to AWS_REGION
        environment variable or us-east-1.

        Args:
            region: AWS region for Bedrock. Defaults to AWS_REGION env var
                   or us-east-1 if not set.

        Raises:
            AWSCredentialsError: If AWS credentials cannot be found.
        """
        self.model_id = EMBEDDING_MODEL_ID
        self.dimensions = EMBEDDING_DIMENSIONS
        self._client = None
        self._region = region

    def _get_client(self) -> Any:
        """Get or create boto3 Bedrock runtime client.

        Returns:
            Boto3 bedrock-runtime client.

        Raises:
            AWSCredentialsError: If credentials cannot be found.
        """
        if self._client is not None:
            return self._client

        try:
            import boto3  # type: ignore[import-not-found]
            from botocore.exceptions import (  # type: ignore[import-not-found]
                NoCredentialsError,
                ProfileNotFound,
            )
        except ImportError:
            raise ImportError(
                "boto3 is required for vector search. "
                "Install with: pip install paper-index-tool[vector] "
                "or: uv sync --extra vector"
            )

        try:
            # Use default credential chain (env vars, profile, IAM role)
            session = boto3.Session(region_name=self._region)
            self._client = session.client("bedrock-runtime")
            logger.debug("Created Bedrock client in region: %s", session.region_name)
            return self._client
        except NoCredentialsError as e:
            raise AWSCredentialsError(str(e))
        except ProfileNotFound as e:
            raise AWSCredentialsError(f"AWS profile not found: {e}")
        except Exception as e:
            raise AWSCredentialsError(f"Failed to create Bedrock client: {e}")

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Input text to embed. Max ~8192 tokens (~38,000 chars).

        Returns:
            List of 1024 floats representing the embedding vector.

        Raises:
            EmbeddingError: If API call fails.
            AWSCredentialsError: If credentials are invalid.

        Example:
            >>> vector = embeddings.embed_text("How do leaders develop?")
            >>> len(vector)
            1024
        """
        if not text or not text.strip():
            raise EmbeddingError("Input text cannot be empty")

        # Truncate if too long (roughly 4.7 chars per token)
        max_chars = int(MAX_INPUT_TOKENS * 4.7)
        if len(text) > max_chars:
            logger.warning(
                "Text truncated from %d to %d chars for embedding",
                len(text),
                max_chars,
            )
            text = text[:max_chars]

        try:
            client = self._get_client()

            # Titan v2 request format
            request_body = json.dumps({"inputText": text})

            response = client.invoke_model(
                modelId=self.model_id,
                body=request_body,
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            embedding = response_body["embedding"]

            logger.debug("Generated embedding with %d dimensions", len(embedding))
            return list(embedding)

        except Exception as e:
            error_str = str(e)
            if "AccessDeniedException" in error_str:
                raise AWSCredentialsError(
                    f"Access denied to model {self.model_id}. "
                    f"Ensure your IAM role has bedrock:InvokeModel permission "
                    f"for this model in your region."
                )
            if "ExpiredTokenException" in error_str:
                raise AWSCredentialsError("AWS session token expired. Please refresh credentials.")
            if "UnrecognizedClientException" in error_str:
                raise AWSCredentialsError("Invalid AWS credentials.")
            raise EmbeddingError(error_str)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Processes texts sequentially. For large batches, consider
        implementing batching with rate limiting.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors (each 1024 floats).

        Raises:
            EmbeddingError: If any API call fails.

        Example:
            >>> vectors = embeddings.embed_texts(["text1", "text2"])
            >>> len(vectors)
            2
        """
        embeddings = []
        for i, text in enumerate(texts):
            logger.debug("Embedding text %d/%d", i + 1, len(texts))
            embedding = self.embed_text(text)
            embeddings.append(embedding)
        return embeddings
