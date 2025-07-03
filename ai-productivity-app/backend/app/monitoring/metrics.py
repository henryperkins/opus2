# backend/app/monitoring/metrics.py
"""Prometheus metrics for embedding operations.

This module provides metrics collection for embedding generation,
including success/failure rates, token usage, and batch sizes.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Optional Prometheus support
try:
    from prometheus_client import Counter, Histogram, Gauge
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

    # Stub implementations for when Prometheus is not available
    class _StubMetric:
        def inc(self, amount=1):
            pass

        def observe(self, value):
            pass

        def set(self, value):
            pass

        def labels(self, **kwargs):
            return self

    Counter = _StubMetric
    Histogram = _StubMetric
    Gauge = _StubMetric


# Metrics definitions
embedding_batches_total = Counter(
    "embedding_batches_total",
    "Total number of embedding batches processed",
    ["status"]
)

embedding_tokens_total = Counter(
    "embedding_tokens_total",
    "Total number of tokens sent for embedding"
)

embedding_batch_size = Histogram(
    "embedding_batch_size",
    "Size of embedding batches",
    buckets=(1, 5, 10, 25, 50, 100, 200)
)

embedding_processing_duration = Histogram(
    "embedding_processing_duration_seconds",
    "Time taken to process embedding batches",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

embedding_queue_length = Gauge(
    "embedding_queue_length",
    "Number of pending embeddings in the queue"
)

embedding_errors_total = Counter(
    "embedding_errors_total",
    "Total number of embedding errors",
    ["error_type"]
)


def record_success(batch_size: int, tokens: int, duration: Optional[float] = None) -> None:
    """Record successful embedding batch processing.

    Args:
        batch_size: Number of texts in the batch
        tokens: Total tokens processed
        duration: Processing time in seconds
    """
    if not HAS_PROMETHEUS:
        return

    embedding_batches_total.labels(status="success").inc()
    embedding_tokens_total.inc(tokens)
    embedding_batch_size.observe(batch_size)

    if duration is not None:
        embedding_processing_duration.observe(duration)


def record_oversize_error(batch_size: int, tokens: int) -> None:
    """Record an oversized batch error.

    Args:
        batch_size: Number of texts in the failed batch
        tokens: Total tokens that caused the failure
    """
    if not HAS_PROMETHEUS:
        return

    embedding_batches_total.labels(status="oversize").inc()
    embedding_errors_total.labels(error_type="oversize").inc()
    embedding_batch_size.observe(batch_size)

    logger.warning(
        "Oversized batch detected: %d texts, %d tokens",
        batch_size, tokens
    )


def record_retry_error(error_type: str) -> None:
    """Record a retryable error.

    Args:
        error_type: Type of error (rate_limit, timeout, network, etc.)
    """
    if not HAS_PROMETHEUS:
        return

    embedding_batches_total.labels(status="error").inc()
    embedding_errors_total.labels(error_type=error_type).inc()


def record_fatal_error(error_type: str) -> None:
    """Record a non-retryable fatal error.

    Args:
        error_type: Type of error (auth_failed, invalid_model, etc.)
    """
    if not HAS_PROMETHEUS:
        return

    embedding_batches_total.labels(status="fatal").inc()
    embedding_errors_total.labels(error_type=error_type).inc()


def update_queue_length(length: int) -> None:
    """Update the embedding queue length metric.

    Args:
        length: Current number of pending embeddings
    """
    if not HAS_PROMETHEUS:
        return

    embedding_queue_length.set(length)


def get_metrics_summary() -> dict:
    """Get a summary of current metrics for logging/debugging.

    Returns:
        Dictionary with metric names and current values
    """
    if not HAS_PROMETHEUS:
        return {"prometheus": "not_available"}

    # This is a simplified summary - in production you might want
    # to actually collect the current metric values
    return {
        "prometheus": "available",
        "metrics_defined": [
            "embedding_batches_total",
            "embedding_tokens_total",
            "embedding_batch_size",
            "embedding_processing_duration",
            "embedding_queue_length",
            "embedding_errors_total"
        ]
    }
