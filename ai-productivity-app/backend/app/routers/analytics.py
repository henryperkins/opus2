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


# ------------------------------------------------------------
# Stubbed metrics for the Embedding dashboard
# ------------------------------------------------------------


class EmbeddingPerformance(BaseModel):
    avg_latency_ms: float = 123.4
    p90_latency_ms: float = 210.0
    throughput_qps: float = 4.2


class EmbeddingStats(BaseModel):
    total_batches_processed: int
    success_rate: float
    avg_tokens_per_doc: float


class HealthIndicators(BaseModel):
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
    response = EmbeddingMetricsResponse(
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
    return response


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

# ---------------------------------------------------------------------------
# Usage statistics – used by Model selection UI
# ---------------------------------------------------------------------------


class UsageStatsResponse(BaseModel):
    requests_today: int = Field(..., alias="requestsToday")
    estimated_cost: float = Field(..., alias="estimatedCost")
    average_latency: float = Field(..., alias="averageLatency")
    error_rate: float = Field(..., alias="errorRate")
    last_used: datetime = Field(..., alias="lastUsed")


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    project_id: str = "current",
    model_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
):
    """Return placeholder usage statistics so the frontend widgets render.

    The implementation is currently a stub that returns randomized numbers.
    Once real usage metrics are available this endpoint should query the
    analytics data store or Prometheus instead of generating real values.
    """
    from random import randint, uniform  # local import to avoid global cost

    return UsageStatsResponse(
        requests_today=randint(20, 120),
        estimated_cost=round(uniform(0.1, 15.0), 2),
        average_latency=round(uniform(300, 1500), 1),
        error_rate=round(uniform(0, 5), 2),
        last_used=datetime.now(timezone.utc),
    )
