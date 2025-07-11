"""Analytics API endpoints (MVP).

The first implementation focuses on *accepting* client-side metrics so the
frontend can send analytics without receiving 404 errors.  The data is logged
server-side for now – a proper persistence layer (database tables, warehouse
export, etc.) can be added later.

Endpoints
---------
POST /api/analytics/batch
    Accepts a JSON body of the shape

        { "metrics": [ {..}, {..} ], "metadata": { .. } }

    and returns `{ "success": true, "received": N }`.

GET /api/analytics/embedding-metrics
    Returns stubbed embedding processing metrics so that the frontend widgets
    in `EmbeddingMetrics.jsx` render meaningful numbers during the transition
    period while the real pipeline is being built.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field, conlist


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class Metric(BaseModel):
    """Generic metric payload – we allow arbitrary keys for flexibility."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sessionId: str | None = None  # camelCase matches the frontend
    userId: int | None = None

    # Additional dynamic fields are permitted
    class Config:
        extra = "allow"


class BatchPayload(BaseModel):
    metrics: conlist(Metric, min_length=1)  # at least one metric
    metadata: Dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# In-memory store – *temporary*
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# In-memory stores (MVP – replace with persistent tables later)
# ---------------------------------------------------------------------------

_METRIC_BUFFER: List[Metric] = []  # generic batch ingest


# Quality metrics for chat responses – keyed by project_id so that the
# frontend can request per-project aggregates.  Each value stores a list of
# floats representing an arbitrary "overall quality" score in the range
# 0-1 (the frontend currently calculates this client-side but also sends the
# full metric payload; we persist `overall` for quick aggregation and keep the
# original record too for future drill-down).

_QUALITY_RAW: List[Dict[str, Any]] = []
_QUALITY_BY_PROJECT: Dict[int, List[float]] = {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def ingest_batch(payload: BatchPayload):
    """Ingest a batch of client-side metrics.

    For the MVP we simply append to an in-memory list and log the receipt so
    that we can validate end-to-end wiring.  Future iterations will stream the
    data into a dedicated table or analytics queue.
    """

    received_count = len(payload.metrics)

    # Store in memory (best-effort)
    try:
        _METRIC_BUFFER.extend(payload.metrics)
        if len(_METRIC_BUFFER) > 10_000:  # simple back-pressure safeguard
            _METRIC_BUFFER[:] = _METRIC_BUFFER[-10_000:]
    except Exception as exc:  # pragma: no cover – extreme edge-case handling
        logger.warning("Failed to buffer analytics metrics: %s", exc, exc_info=True)

    logger.info(
        "Analytics batch received – metrics=%s, meta=%s", received_count, payload.metadata
    )

    return {"success": True, "received": received_count}


# ---------------------------------------------------------------------------
# Lightweight usage statistics (placeholder)
# ---------------------------------------------------------------------------


class UsageStats(BaseModel):
    """Minimal usage statistics returned to the frontend.

    The schema mirrors the fields consumed by the React hooks so that the UI
    does not break while the real implementation is being built server-side.
    All numbers are *approximate* placeholders calculated from the in-memory
    metric buffer to provide deterministic, non-random behaviour that still
    changes over time during a single server run.
    """

    project_id: str
    model_id: str | None = None
    requestsToday: int
    estimatedCost: float
    averageLatency: float | None = None
    errorRate: float | None = None
    lastUsed: datetime


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    project_id: str, model_id: str | None = None  # query params from the frontend
):
    """Return *very* rough usage statistics so that the dashboard widgets render.

    The current implementation is intentionally simple – it only examines the
    in-memory metric buffer populated by the `/batch` endpoint and derives a
    handful of aggregate numbers that the frontend expects.  Once a proper
    analytics pipeline lands we can swap this out for real metrics without
    changing the client code.
    """

    # Count how many metrics belong to *today* so that the number goes back to
    # zero after midnight UTC – a close enough proxy for "daily requests" in
    # the interim.
    today = datetime.now(timezone.utc).date()
    requests_today = sum(1 for m in _METRIC_BUFFER if m.timestamp.date() == today)

    # Naïve cost estimation: assume $0.002 per request as a placeholder so that
    # the value feels realistic to the user.
    estimated_cost = round(requests_today * 0.002, 4)

    # Latency / error-rate are not tracked yet – return None so the UI can
    # decide how to display missing data gracefully.
    return UsageStats(
        project_id=project_id,
        model_id=model_id,
        requestsToday=requests_today,
        estimatedCost=estimated_cost,
        averageLatency=None,
        errorRate=None,
        lastUsed=datetime.now(timezone.utc),
    )
# ---------------------------------------------------------------------------
# NOTE:
# If you later need more granular or date-range-filtered usage statistics,
# expose a *separate* route such as `/usage/history` or `/usage/detailed`
# instead of redefining `/usage` – this avoids duplicate-route errors and keeps
# the API surface explicit.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Stubbed embedding metrics models (placeholder until real pipeline ready)
# ---------------------------------------------------------------------------


class EmbeddingPerformance(BaseModel):
    """Simplified performance KPIs for the embedding worker pipeline."""

    avg_latency_ms: float = 123.4
    p90_latency_ms: float = 210.0
    throughput_qps: float = 4.2


class EmbeddingStats(BaseModel):
    """High-level statistics about processed embedding batches."""

    total_batches_processed: int
    success_rate: float  # between 0-1
    avg_tokens_per_doc: float


class HealthIndicators(BaseModel):
    """Binary health indicators for key sub-systems."""

    vector_db_connected: bool
    queue_backlog_ok: bool
    last_worker_heartbeat_ok: bool


class EmbeddingMetricsResponse(BaseModel):
    embedding_stats: EmbeddingStats
    performance_metrics: EmbeddingPerformance
    health_indicators: HealthIndicators


@router.get("/embedding-metrics", response_model=EmbeddingMetricsResponse)
async def get_embedding_metrics():
    """Return placeholder embedding metrics so the UI can render."""

    # The numbers below are illustrative defaults.
    return EmbeddingMetricsResponse(
        embedding_stats=EmbeddingStats(
            total_batches_processed=1420,
            success_rate=0.987,
            avg_tokens_per_doc=255.3,
        ),
        performance_metrics=EmbeddingPerformance(),
        health_indicators=HealthIndicators(
            vector_db_connected=True,
            queue_backlog_ok=True,
            last_worker_heartbeat_ok=True,
        ),
    )


# ---------------------------------------------------------------------------
# Response quality tracking – used by ResponseQuality.jsx
# ---------------------------------------------------------------------------


class QualityMetric(BaseModel):
    """Quality metric sent from the client after the model produced a reply."""

    project_id: int
    session_id: int | None = None
    message_id: int | None = None

    # Sub-scores (0-1 floats)
    relevance: float | None = None
    accuracy: float | None = None
    helpfulness: float | None = None
    clarity: float | None = None
    completeness: float | None = None

    overall: float  # client calculates weighted score; required so we can do quick avg

    # misc
    model: str | None = None
    response_time_ms: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.post("/quality", status_code=status.HTTP_202_ACCEPTED)
async def track_quality(metric: QualityMetric):
    """Ingest a single quality metric record."""

    _QUALITY_RAW.append(metric.dict())

    # Aggregate per project (simple running list)
    bucket = _QUALITY_BY_PROJECT.setdefault(metric.project_id, [])
    bucket.append(metric.overall)
    if len(bucket) > 5000:  # keep memory bounded per project
        bucket[:] = bucket[-5000:]

    logger.debug(
        "Quality metric received – project=%s overall=%.3f model=%s", metric.project_id, metric.overall, metric.model
    )

    return {"success": True}


class ProjectQualitySummary(BaseModel):
    project_id: int
    sample_size: int
    average_score: float


@router.get("/quality/{project_id}", response_model=ProjectQualitySummary)
async def get_project_quality(project_id: int):
    """Return simple average of `overall` scores for the given project."""

    scores = _QUALITY_BY_PROJECT.get(project_id) or []
    if not scores:
        # Graceful empty response instead of 404 so UI shows 0
        return ProjectQualitySummary(project_id=project_id, sample_size=0, average_score=0.0)

    avg = sum(scores) / len(scores)
    return ProjectQualitySummary(project_id=project_id, sample_size=len(scores), average_score=avg)
