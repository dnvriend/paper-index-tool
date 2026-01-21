"""Error classes for vector search module.

This module defines custom exceptions for vector search operations,
providing agent-friendly error messages with actionable guidance.

Exceptions:
    VectorSearchError: Base exception for vector search operations.
    EmbeddingError: Failed to generate embeddings via Bedrock.
    IndexNotFoundError: Vector index not found.
    AWSCredentialsError: AWS credentials not configured.
"""


class VectorSearchError(Exception):
    """Base exception for vector search operations.

    All vector search related exceptions inherit from this class,
    allowing for broad exception handling when needed.

    Example:
        >>> try:
        ...     searcher.search("query")
        ... except VectorSearchError as e:
        ...     print(f"Search failed: {e}")
    """

    pass


class EmbeddingError(VectorSearchError):
    """Failed to generate embedding via AWS Bedrock.

    Raised when the Bedrock API fails to generate embeddings,
    which can happen due to API errors, rate limits, or invalid input.

    Attributes:
        message: Error description with guidance.

    Example:
        >>> raise EmbeddingError("API returned error: ThrottlingException")
    """

    def __init__(self, message: str) -> None:
        """Initialize with descriptive message.

        Args:
            message: Error description including the underlying cause.
        """
        super().__init__(
            f"Failed to generate embedding: {message}. "
            f"Check AWS credentials and Bedrock model access. "
            f"Ensure you have access to amazon.titan-embed-text-v2:0 in your region."
        )


class IndexNotFoundError(VectorSearchError):
    """Vector index not found.

    Raised when attempting to search but the FAISS index has not been built.
    The user needs to run the reindex command first.

    Example:
        >>> raise IndexNotFoundError()
    """

    def __init__(self) -> None:
        """Initialize with guidance message."""
        super().__init__(
            "Vector index not found. "
            "Run 'paper-index-tool reindex --vectors' to build the semantic search index. "
            "This requires AWS credentials with Bedrock access."
        )


class AWSCredentialsError(VectorSearchError):
    """AWS credentials not configured.

    Raised when boto3 cannot find valid AWS credentials for Bedrock access.
    The user needs to configure AWS credentials via environment variables
    or AWS credentials file.

    Example:
        >>> raise AWSCredentialsError("No credentials found")
    """

    def __init__(self, message: str) -> None:
        """Initialize with descriptive message.

        Args:
            message: Details about the credential error.
        """
        super().__init__(
            f"AWS credentials not configured: {message}. "
            f"Configure credentials using one of: "
            f"1) AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables, "
            f"2) AWS_PROFILE environment variable pointing to a profile in ~/.aws/credentials, "
            f"3) IAM role (if running on AWS). "
            f"Ensure the credentials have bedrock:InvokeModel permission."
        )
