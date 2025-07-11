# backend/app/exceptions.py
"""Custom exceptions for better error handling."""
from typing import Optional, Dict, Any


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class LLMException(AppException):
    """Exceptions related to LLM operations."""

    pass


class ModelNotFoundException(LLMException):
    """Raised when requested model is not found."""

    def __init__(self, model: str, provider: str):
        super().__init__(
            f"Model '{model}' not found for provider '{provider}'",
            error_code="MODEL_NOT_FOUND",
            details={"model": model, "provider": provider},
        )


class LLMRateLimitException(LLMException):
    """Raised when LLM rate limit is exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        super().__init__(
            "LLM rate limit exceeded",
            error_code="LLM_RATE_LIMIT",
            details={"retry_after": retry_after},
        )


class LLMTimeoutException(LLMException):
    """Raised when LLM request times out."""

    def __init__(self, timeout: int):
        super().__init__(
            f"LLM request timed out after {timeout} seconds",
            error_code="LLM_TIMEOUT",
            details={"timeout": timeout},
        )


class EmbeddingException(AppException):
    """Exceptions related to embedding operations."""

    pass


class VectorDimensionMismatchException(EmbeddingException):
    """Raised when embedding dimensions don't match."""

    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"Embedding dimension mismatch: expected {expected}, got {actual}",
            error_code="DIMENSION_MISMATCH",
            details={"expected": expected, "actual": actual},
        )
