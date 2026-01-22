"""AWS Bedrock embeddings client for vector search.

This module provides a client for generating text embeddings using
AWS Bedrock embedding models. Embeddings are used for semantic
search across papers, books, and media.

Classes:
    BedrockEmbeddings: Client for AWS Bedrock text embeddings.
    EmbeddingStats: Statistics from embedding generation.
    EmbeddingModelConfig: Configuration for an embedding model.

Supported Models:
    titan-v1: amazon.titan-embed-text-v1 (1536 dims)
    titan-v2: amazon.titan-embed-text-v2:0 (1024 dims)
    cohere-en: cohere.embed-english-v3 (1024 dims)
    cohere-multi: cohere.embed-multilingual-v3 (1024 dims)
    nova: amazon.nova-2-multimodal-embeddings-v1:0 (256/512/1024/3072 dims)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from paper_index_tool.logging_config import get_logger
from paper_index_tool.vector.errors import AWSCredentialsError, EmbeddingError

logger = get_logger(__name__)


# =============================================================================
# Model Configuration
# =============================================================================


@dataclass
class EmbeddingModelConfig:
    """Configuration for an embedding model.

    Attributes:
        model_id: AWS Bedrock model identifier.
        default_dimensions: Default embedding dimensions.
        supported_dimensions: List of supported dimension values (None if not configurable).
        max_input_tokens: Maximum input tokens.
        price_per_1000_tokens: Cost per 1000 input tokens in USD.
    """

    model_id: str
    default_dimensions: int
    supported_dimensions: list[int] | None
    max_input_tokens: int
    price_per_1000_tokens: float


# Supported embedding models
EMBEDDING_MODELS: dict[str, EmbeddingModelConfig] = {
    "titan-v1": EmbeddingModelConfig(
        model_id="amazon.titan-embed-text-v1",
        default_dimensions=1536,
        supported_dimensions=None,  # Fixed
        max_input_tokens=8192,
        price_per_1000_tokens=0.0001,
    ),
    "titan-v2": EmbeddingModelConfig(
        model_id="amazon.titan-embed-text-v2:0",
        default_dimensions=1024,
        supported_dimensions=None,  # Fixed
        max_input_tokens=8192,
        price_per_1000_tokens=0.00002,
    ),
    "cohere-en": EmbeddingModelConfig(
        model_id="cohere.embed-english-v3",
        default_dimensions=1024,
        supported_dimensions=None,  # Fixed
        max_input_tokens=512,
        price_per_1000_tokens=0.0001,
    ),
    "cohere-multi": EmbeddingModelConfig(
        model_id="cohere.embed-multilingual-v3",
        default_dimensions=1024,
        supported_dimensions=None,  # Fixed
        max_input_tokens=512,
        price_per_1000_tokens=0.0001,
    ),
    "nova": EmbeddingModelConfig(
        model_id="amazon.nova-2-multimodal-embeddings-v1:0",
        default_dimensions=1024,
        supported_dimensions=[256, 512, 1024, 3072],
        max_input_tokens=8000,  # Nova supports longer input
        price_per_1000_tokens=0.00001,
    ),
}

# Default model for backward compatibility
DEFAULT_MODEL = "titan-v2"

# Default region - us-east-1 is required for Nova embedding model
DEFAULT_REGION = "us-east-1"

# Legacy constants for backward compatibility
EMBEDDING_MODEL_ID = EMBEDDING_MODELS[DEFAULT_MODEL].model_id
EMBEDDING_DIMENSIONS = EMBEDDING_MODELS[DEFAULT_MODEL].default_dimensions
MAX_INPUT_TOKENS = EMBEDDING_MODELS[DEFAULT_MODEL].max_input_tokens
PRICE_PER_1000_TOKENS = EMBEDDING_MODELS[DEFAULT_MODEL].price_per_1000_tokens


def get_model_config(model_name: str) -> EmbeddingModelConfig:
    """Get configuration for a model by name.

    Args:
        model_name: CLI model name (e.g., "nova", "titan-v2").

    Returns:
        EmbeddingModelConfig for the model.

    Raises:
        ValueError: If model name is not recognized.
    """
    if model_name not in EMBEDDING_MODELS:
        valid_models = ", ".join(EMBEDDING_MODELS.keys())
        raise ValueError(f"Unknown embedding model: '{model_name}'. Valid models: {valid_models}")
    return EMBEDDING_MODELS[model_name]


def validate_dimensions(model_name: str, dimensions: int | None) -> int:
    """Validate and return dimensions for a model.

    Args:
        model_name: CLI model name.
        dimensions: Requested dimensions (None for default).

    Returns:
        Validated dimensions.

    Raises:
        ValueError: If dimensions are not supported by the model.
    """
    config = get_model_config(model_name)

    if dimensions is None:
        return config.default_dimensions

    if config.supported_dimensions is None:
        # Model has fixed dimensions
        if dimensions != config.default_dimensions:
            raise ValueError(
                f"Model '{model_name}' has fixed dimensions: {config.default_dimensions}. "
                f"Cannot use dimensions={dimensions}."
            )
        return dimensions

    if dimensions not in config.supported_dimensions:
        valid_dims = ", ".join(str(d) for d in config.supported_dimensions)
        raise ValueError(
            f"Model '{model_name}' supports dimensions: {valid_dims}. "
            f"Cannot use dimensions={dimensions}."
        )
    return dimensions


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
    def from_tokens(
        cls,
        total_tokens: int,
        num_texts: int,
        price_per_1000_tokens: float | None = None,
    ) -> EmbeddingStats:
        """Create stats from token count.

        Args:
            total_tokens: Total tokens processed.
            num_texts: Number of texts embedded.
            price_per_1000_tokens: Price per 1000 tokens. Defaults to titan-v2 price.
        """
        price = price_per_1000_tokens or PRICE_PER_1000_TOKENS
        cost = (total_tokens / 1000) * price
        return cls(total_tokens=total_tokens, total_cost=cost, num_texts=num_texts)


class BedrockEmbeddings:
    """AWS Bedrock embeddings client supporting multiple models.

    Generates embeddings for semantic search using configurable embedding models.
    Uses boto3 with standard credential chain (env vars, AWS profile, IAM role).

    Supported models:
        - titan-v1: amazon.titan-embed-text-v1 (1536 dims)
        - titan-v2: amazon.titan-embed-text-v2:0 (1024 dims) - default
        - cohere-en: cohere.embed-english-v3 (1024 dims)
        - cohere-multi: cohere.embed-multilingual-v3 (1024 dims)
        - nova: amazon.nova-embed-text-v1:0 (256/512/1024 dims configurable)

    Attributes:
        model_id: Bedrock model identifier.
        model_name: CLI model name.
        dimensions: Embedding vector dimensions.
        config: Model configuration.

    Example:
        >>> embeddings = BedrockEmbeddings(model_name="nova", dimensions=1024)
        >>> vector = embeddings.embed_text("What is leadership?")
        >>> len(vector)
        1024
    """

    def __init__(
        self,
        region: str | None = None,
        model_name: str = DEFAULT_MODEL,
        dimensions: int | None = None,
        max_pool_connections: int = 50,
    ) -> None:
        """Initialize Bedrock embeddings client.

        Uses boto3 credential chain: environment variables, AWS profile,
        or IAM role. Region can be specified or defaults to AWS_REGION
        environment variable or us-east-1.

        Args:
            region: AWS region for Bedrock. Defaults to us-east-1 (required
                   for Nova embedding model).
            model_name: CLI model name (e.g., "nova", "titan-v2").
            dimensions: Embedding dimensions. Required for configurable models.
            max_pool_connections: Maximum HTTP pool connections for concurrent
                requests. Should match or exceed max_workers in embed_texts().
                Default: 50.

        Raises:
            AWSCredentialsError: If AWS credentials cannot be found.
            ValueError: If model or dimensions are invalid.
        """
        self.config = get_model_config(model_name)
        self.model_name = model_name
        self.model_id = self.config.model_id
        self.dimensions = validate_dimensions(model_name, dimensions)
        self._client = None
        self._region = region or DEFAULT_REGION
        self._max_pool_connections = max_pool_connections

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
            from botocore.config import Config  # type: ignore[import-not-found]
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
            # Configure connection pool for concurrent requests
            boto_config = Config(
                max_pool_connections=self._max_pool_connections,
                retries={"max_attempts": 3, "mode": "adaptive"},
            )

            # Use default credential chain (env vars, profile, IAM role)
            session = boto3.Session(region_name=self._region)
            self._client = session.client("bedrock-runtime", config=boto_config)
            logger.debug(
                "Created Bedrock client in region: %s (pool_connections=%d)",
                session.region_name,
                self._max_pool_connections,
            )
            return self._client
        except NoCredentialsError as e:
            raise AWSCredentialsError(str(e))
        except ProfileNotFound as e:
            raise AWSCredentialsError(f"AWS profile not found: {e}")
        except Exception as e:
            raise AWSCredentialsError(f"Failed to create Bedrock client: {e}")

    def _build_request_body(self, text: str, purpose: str = "GENERIC_INDEX") -> str:
        """Build model-specific request body.

        Args:
            text: Input text to embed.
            purpose: Embedding purpose for Nova model (GENERIC_INDEX or TEXT_RETRIEVAL).

        Returns:
            JSON-encoded request body.
        """
        if self.model_name.startswith("cohere"):
            # Cohere models use different format
            input_type = "search_query" if purpose == "TEXT_RETRIEVAL" else "search_document"
            return json.dumps(
                {
                    "texts": [text],
                    "input_type": input_type,
                }
            )
        elif self.model_name == "nova":
            # Nova multimodal embeddings model - different API format
            return json.dumps(
                {
                    "schemaVersion": "nova-multimodal-embed-v1",
                    "taskType": "SINGLE_EMBEDDING",
                    "singleEmbeddingParams": {
                        "embeddingPurpose": purpose,
                        "embeddingDimension": self.dimensions,
                        "text": {"truncationMode": "END", "value": text},
                    },
                }
            )
        else:
            # Titan models
            return json.dumps({"inputText": text})

    def _parse_response(
        self, response_body: dict[str, Any], text_length: int = 0
    ) -> tuple[list[float], int]:
        """Parse model-specific response.

        Args:
            response_body: Parsed JSON response from Bedrock.
            text_length: Length of input text for token estimation.

        Returns:
            Tuple of (embedding vector, token count).
        """
        if self.model_name.startswith("cohere"):
            # Cohere returns list of embeddings
            embedding = response_body["embeddings"][0]
            # Cohere doesn't return token count in the same way
            token_count = (
                response_body.get("meta", {}).get("billed_units", {}).get("input_tokens", 0)
            )
        elif self.model_name == "nova":
            # Nova returns embeddings array with embedding objects
            embedding = response_body["embeddings"][0]["embedding"]
            # Estimate tokens (~4 chars per token)
            token_count = text_length // 4
        else:
            # Titan models
            embedding = response_body["embedding"]
            token_count = response_body.get("inputTextTokenCount", 0)

        return list(embedding), token_count

    def _embed_text_with_tokens(
        self, text: str, purpose: str = "GENERIC_INDEX"
    ) -> tuple[list[float], int]:
        """Generate embedding vector and return token count.

        Args:
            text: Input text to embed.
            purpose: Embedding purpose for Nova model (GENERIC_INDEX or TEXT_RETRIEVAL).

        Returns:
            Tuple of (embedding vector, input token count).

        Raises:
            EmbeddingError: If API call fails.
            AWSCredentialsError: If credentials are invalid.
        """
        if not text or not text.strip():
            raise EmbeddingError("Input text cannot be empty")

        # Truncate if too long (roughly 4.7 chars per token)
        max_chars = int(self.config.max_input_tokens * 4.7)
        if len(text) > max_chars:
            logger.warning(
                "Text truncated from %d to %d chars for embedding",
                len(text),
                max_chars,
            )
            text = text[:max_chars]

        try:
            client = self._get_client()

            request_body = self._build_request_body(text, purpose)

            response = client.invoke_model(
                modelId=self.model_id,
                body=request_body,
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            embedding, token_count = self._parse_response(response_body, len(text))

            logger.debug(
                "Generated embedding with %d dimensions, %d tokens", len(embedding), token_count
            )
            return embedding, token_count

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

    def embed_text(self, text: str, purpose: str = "GENERIC_INDEX") -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Input text to embed. Max ~8192 tokens (~38,000 chars).
            purpose: Embedding purpose for Nova model:
                    - GENERIC_INDEX: for indexing documents (default)
                    - TEXT_RETRIEVAL: for search queries

        Returns:
            List of floats representing the embedding vector.

        Raises:
            EmbeddingError: If API call fails.
            AWSCredentialsError: If credentials are invalid.

        Example:
            >>> vector = embeddings.embed_text("How do leaders develop?")
            >>> len(vector)
            1024
        """
        embedding, _ = self._embed_text_with_tokens(text, purpose)
        return embedding

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query.

        Uses TEXT_RETRIEVAL purpose for Nova models, which is optimized
        for query embedding vs document embedding.

        Args:
            query: Search query text.

        Returns:
            Embedding vector optimized for search.

        Example:
            >>> vector = embeddings.embed_query("How do leaders develop?")
        """
        return self.embed_text(query, purpose="TEXT_RETRIEVAL")

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
        stats = EmbeddingStats.from_tokens(
            total_tokens, len(texts), self.config.price_per_1000_tokens
        )

        return embeddings, stats
