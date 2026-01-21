"""AWS Bedrock embeddings client for vector search.

This module provides a client for generating text embeddings using
AWS Bedrock's Titan embedding model. Embeddings are used for semantic
search across papers, books, and media.

Classes:
    BedrockEmbeddings: Client for AWS Bedrock text embeddings.
    EmbeddingStats: Statistics from embedding generation.

Model:
    amazon.titan-embed-text-v2:0
    - Dimensions: 1024
    - Max input tokens: 8192
    - Languages: English (100+ in preview)
    - Price: $0.00002 per 1000 input tokens
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from paper_index_tool.logging_config import get_logger
from paper_index_tool.vector.errors import AWSCredentialsError, EmbeddingError

logger = get_logger(__name__)

# Model configuration
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024
MAX_INPUT_TOKENS = 8192
PRICE_PER_1000_TOKENS = 0.00002  # USD


@dataclass
class EmbeddingStats:
    """Statistics from embedding generation.

    Attributes:
        total_tokens: Total number of input tokens processed.
        total_cost: Total cost in USD.
        num_texts: Number of texts embedded.
    """

    total_tokens: int
    total_cost: float
    num_texts: int

    @classmethod
    def from_tokens(cls, total_tokens: int, num_texts: int) -> EmbeddingStats:
        """Create stats from token count."""
        cost = (total_tokens / 1000) * PRICE_PER_1000_TOKENS
        return cls(total_tokens=total_tokens, total_cost=cost, num_texts=num_texts)


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

    def _embed_text_with_tokens(self, text: str) -> tuple[list[float], int]:
        """Generate embedding vector and return token count.

        Args:
            text: Input text to embed. Max ~8192 tokens (~38,000 chars).

        Returns:
            Tuple of (embedding vector, input token count).

        Raises:
            EmbeddingError: If API call fails.
            AWSCredentialsError: If credentials are invalid.
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
            token_count = response_body.get("inputTextTokenCount", 0)

            logger.debug(
                "Generated embedding with %d dimensions, %d tokens", len(embedding), token_count
            )
            return list(embedding), token_count

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
        embedding, _ = self._embed_text_with_tokens(text)
        return embedding

    def embed_texts(
        self, texts: list[str], show_progress: bool = True, max_workers: int | None = None
    ) -> tuple[list[list[float]], EmbeddingStats]:
        """Generate embeddings for multiple texts in parallel.

        Processes texts concurrently using ThreadPoolExecutor for I/O-bound
        API calls to AWS Bedrock.

        Args:
            texts: List of texts to embed.
            show_progress: If True, display tqdm progress bar.
            max_workers: Number of parallel workers. Defaults to CPU count.

        Returns:
            Tuple of (embeddings list, stats with token count and cost).

        Raises:
            EmbeddingError: If any API call fails.

        Example:
            >>> vectors, stats = embeddings.embed_texts(["text1", "text2"])
            >>> len(vectors)
            2
            >>> print(f"Cost: ${stats.total_cost:.6f}")
        """
        import os
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from tqdm import tqdm

        if not texts:
            return [], EmbeddingStats(total_tokens=0, total_cost=0.0, num_texts=0)

        num_workers = max_workers or os.cpu_count() or 1
        results: dict[int, tuple[list[float], int]] = {}

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tasks with their indices to preserve order
            future_to_idx = {
                executor.submit(self._embed_text_with_tokens, text): idx
                for idx, text in enumerate(texts)
            }

            # Process completed futures with progress bar
            completed_futures = as_completed(future_to_idx)
            if show_progress:
                completed_futures = tqdm(  # type: ignore[assignment]
                    completed_futures,
                    total=len(texts),
                    desc="Generating embeddings",
                    unit="chunk",
                )

            for future in completed_futures:
                idx = future_to_idx[future]
                results[idx] = future.result()

        # Calculate totals and return in original order
        embeddings = [results[i][0] for i in range(len(texts))]
        total_tokens = sum(results[i][1] for i in range(len(texts)))
        stats = EmbeddingStats.from_tokens(total_tokens, len(texts))

        return embeddings, stats
