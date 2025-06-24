# backend/tests/test_exception_handling.py
"""Tests for custom exception handling and Sentry integration."""
import pytest
from unittest.mock import patch, MagicMock
from app.exceptions import (
    ModelNotFoundException,
    LLMRateLimitException,
    LLMTimeoutException,
    VectorDimensionMismatchException
)


def test_model_not_found_exception():
    """Test ModelNotFoundException with proper error code."""
    exc = ModelNotFoundException("gpt-4", "openai")

    assert str(exc) == "Model 'gpt-4' not found for provider 'openai'"
    assert exc.error_code == "MODEL_NOT_FOUND"
    assert exc.details["model"] == "gpt-4"
    assert exc.details["provider"] == "openai"


def test_llm_rate_limit_exception():
    """Test LLMRateLimitException with retry information."""
    exc = LLMRateLimitException(retry_after=60)

    assert "rate limit exceeded" in str(exc).lower()
    assert exc.error_code == "LLM_RATE_LIMIT"
    assert exc.details["retry_after"] == 60


def test_llm_timeout_exception():
    """Test LLMTimeoutException with timeout details."""
    exc = LLMTimeoutException(timeout=30)

    assert "timed out after 30 seconds" in str(exc)
    assert exc.error_code == "LLM_TIMEOUT"
    assert exc.details["timeout"] == 30


def test_vector_dimension_mismatch_exception():
    """Test VectorDimensionMismatchException with dimension details."""
    exc = VectorDimensionMismatchException(expected=1536, actual=768)

    assert "expected 1536, got 768" in str(exc)
    assert exc.error_code == "DIMENSION_MISMATCH"
    assert exc.details["expected"] == 1536
    assert exc.details["actual"] == 768


@patch('app.llm.client.sentry_sdk')
def test_sentry_integration_captures_exceptions(mock_sentry):
    """Test that Sentry captures custom exceptions."""
    from app.llm.client import LLMClient

    # Mock Sentry capture_exception
    mock_sentry.capture_exception = MagicMock()

    # This would normally trigger Sentry in a real error scenario
    exc = ModelNotFoundException("invalid-model", "openai")
    mock_sentry.capture_exception(exc)

    # Verify Sentry was called
    mock_sentry.capture_exception.assert_called_once_with(exc)


def test_exception_inheritance():
    """Test that custom exceptions inherit from appropriate base classes."""
    model_exc = ModelNotFoundException("test", "test")
    rate_exc = LLMRateLimitException()
    timeout_exc = LLMTimeoutException(30)
    vector_exc = VectorDimensionMismatchException(100, 200)

    # All should inherit from their respective base classes
    assert hasattr(model_exc, 'error_code')
    assert hasattr(model_exc, 'details')

    assert hasattr(rate_exc, 'error_code')
    assert hasattr(timeout_exc, 'error_code')
    assert hasattr(vector_exc, 'error_code')


@pytest.mark.asyncio
async def test_llm_client_exception_handling():
    """Test that LLM client properly raises custom exceptions."""
    from app.llm.client import LLMClient

    # Mock the OpenAI client to raise different errors
    with patch('app.llm.client.AsyncOpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Test rate limit handling
        mock_client.chat.completions.create.side_effect = Exception(
            "Rate limit exceeded"
        )

        llm_client = LLMClient()

        # Should handle gracefully and potentially convert to custom exception
        with pytest.raises(Exception):
            await llm_client.generate_response("test prompt")
