"""Cost tracking service for monitoring LLM usage and expenses."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from decimal import Decimal, ROUND_HALF_UP
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel, Field

from app.models.config import ModelConfiguration, ModelUsageMetrics
from app.models.user import User
from app.models.chat import ChatSession
from app.database import get_db

logger = logging.getLogger(__name__)


class UsageEvent(BaseModel):
    """Represents a single usage event for cost tracking."""

    model_id: str
    provider: str
    user_id: Optional[int] = None
    session_id: Optional[str] = None

    # Token usage
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    # Performance metrics
    response_time_ms: float = Field(ge=0)
    success: bool = True

    # Context information
    feature: Optional[str] = None  # e.g., "chat", "search", "analysis"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CostCalculation(BaseModel):
    """Result of cost calculation for a usage event."""

    input_cost: Decimal = Field(decimal_places=6)
    output_cost: Decimal = Field(decimal_places=6)
    total_cost: Decimal = Field(decimal_places=6)

    # Rate information
    input_rate_per_1k: Decimal = Field(decimal_places=6)
    output_rate_per_1k: Decimal = Field(decimal_places=6)

    # Currency
    currency: str = "USD"


class UsageAggregates(BaseModel):
    """Aggregated usage statistics for a time period."""

    model_id: str
    period_start: datetime
    period_end: datetime

    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: Decimal = Field(default=Decimal("0.00"), decimal_places=2)

    avg_response_time_ms: Optional[float] = None
    success_rate: Optional[float] = None
    avg_user_rating: Optional[float] = None

    detailed_metrics: Dict[str, Any] = Field(default_factory=dict)


class CostTrackingService:
    """Service for tracking LLM usage costs and performance metrics."""

    def __init__(self, db: Session):
        self.db = db
        self._cost_cache: Dict[str, CostCalculation] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._last_cache_update = datetime.now(timezone.utc)

    async def calculate_cost(self, event: UsageEvent) -> CostCalculation:
        """Calculate cost for a usage event."""

        # Check if we have cached cost rates
        cache_key = f"{event.model_id}_{event.provider}"
        if self._is_cache_valid() and cache_key in self._cost_cache:
            cached_calc = self._cost_cache[cache_key]
            return CostCalculation(
                input_cost=cached_calc.input_rate_per_1k
                * Decimal(event.input_tokens)
                / 1000,
                output_cost=cached_calc.output_rate_per_1k
                * Decimal(event.output_tokens)
                / 1000,
                total_cost=cached_calc.input_rate_per_1k
                * Decimal(event.input_tokens)
                / 1000
                + cached_calc.output_rate_per_1k * Decimal(event.output_tokens) / 1000,
                input_rate_per_1k=cached_calc.input_rate_per_1k,
                output_rate_per_1k=cached_calc.output_rate_per_1k,
                currency="USD",
            )

        # Fetch model configuration for pricing
        model_config = (
            self.db.query(ModelConfiguration)
            .filter(
                ModelConfiguration.model_id == event.model_id,
                ModelConfiguration.provider == event.provider,
            )
            .first()
        )

        # ------------------------------------------------------------------
        # Fallback – provider-agnostic lookup
        # ------------------------------------------------------------------
        # The *model_configurations* table uses the **model_id** as the sole
        # primary key which means only a *single* entry can exist for, say,
        # ``gpt-4o``.  Yet cost-tracking events often carry provider-specific
        # identifiers ("azure", "openai", …).  Instead of duplicating the full
        # catalogue for every provider we gracefully fall back to a
        # *provider-agnostic* lookup when the initial query misses so that
        # accurate pricing data is still applied.
        if not model_config:
            model_config = (
                self.db.query(ModelConfiguration)
                .filter(ModelConfiguration.model_id == event.model_id)
                .first()
            )

        if not model_config:
            logger.warning(
                "Model configuration not found for %s (%s) – using default pricing",
                event.model_id,
                event.provider,
            )
            input_rate = Decimal("0.001")  # $0.001 per 1K tokens
            output_rate = Decimal("0.002")  # $0.002 per 1K tokens
        else:
            input_rate = Decimal(str(model_config.cost_input_per_1k or 0.001))
            output_rate = Decimal(str(model_config.cost_output_per_1k or 0.002))

        # Calculate costs
        input_cost = (input_rate * Decimal(event.input_tokens) / 1000).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        output_cost = (output_rate * Decimal(event.output_tokens) / 1000).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
        total_cost = input_cost + output_cost

        # Cache the rates
        self._cost_cache[cache_key] = CostCalculation(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            input_rate_per_1k=input_rate,
            output_rate_per_1k=output_rate,
            currency="USD",
        )

        return CostCalculation(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            input_rate_per_1k=input_rate,
            output_rate_per_1k=output_rate,
            currency="USD",
        )

    def _is_cache_valid(self) -> bool:
        """Check if cost cache is still valid."""
        return datetime.now(timezone.utc) - self._last_cache_update < self._cache_ttl

    async def record_usage(self, event: UsageEvent) -> CostCalculation:
        """Record a usage event and return cost calculation."""

        try:
            # Calculate cost
            cost_calc = await self.calculate_cost(event)

            # Get or create usage metrics record for current hour
            period_start = event.timestamp.replace(minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(hours=1)

            usage_metric = (
                self.db.query(ModelUsageMetrics)
                .filter(
                    ModelUsageMetrics.model_id == event.model_id,
                    ModelUsageMetrics.period_start == period_start,
                    ModelUsageMetrics.period_end == period_end,
                )
                .first()
            )

            if not usage_metric:
                usage_metric = ModelUsageMetrics(
                    model_id=event.model_id,
                    period_start=period_start,
                    period_end=period_end,
                    total_requests=0,
                    total_tokens_input=0,
                    total_tokens_output=0,
                    total_cost=0.0,
                    detailed_metrics={},
                )
                self.db.add(usage_metric)

            # Update metrics
            usage_metric.total_requests += 1
            usage_metric.total_tokens_input += event.input_tokens
            usage_metric.total_tokens_output += event.output_tokens
            usage_metric.total_cost += float(cost_calc.total_cost)

            # Update average response time
            if usage_metric.avg_response_time_ms is None:
                usage_metric.avg_response_time_ms = event.response_time_ms
            else:
                # Calculate running average
                total_time = usage_metric.avg_response_time_ms * (
                    usage_metric.total_requests - 1
                )
                usage_metric.avg_response_time_ms = (
                    total_time + event.response_time_ms
                ) / usage_metric.total_requests

            # Update success rate
            if usage_metric.success_rate is None:
                usage_metric.success_rate = 100.0 if event.success else 0.0
            else:
                # Calculate running success rate
                total_success = (usage_metric.success_rate / 100.0) * (
                    usage_metric.total_requests - 1
                )
                if event.success:
                    total_success += 1
                usage_metric.success_rate = (
                    total_success / usage_metric.total_requests
                ) * 100.0

            # Update detailed metrics
            if not usage_metric.detailed_metrics:
                usage_metric.detailed_metrics = {}

            # Track by feature
            if event.feature:
                feature_key = f"feature_{event.feature}"
                if feature_key not in usage_metric.detailed_metrics:
                    usage_metric.detailed_metrics[feature_key] = {
                        "requests": 0,
                        "cost": 0.0,
                    }
                usage_metric.detailed_metrics[feature_key]["requests"] += 1
                usage_metric.detailed_metrics[feature_key]["cost"] += float(
                    cost_calc.total_cost
                )

            # Track by user if available
            if event.user_id:
                user_key = f"user_{event.user_id}"
                if user_key not in usage_metric.detailed_metrics:
                    usage_metric.detailed_metrics[user_key] = {
                        "requests": 0,
                        "cost": 0.0,
                    }
                usage_metric.detailed_metrics[user_key]["requests"] += 1
                usage_metric.detailed_metrics[user_key]["cost"] += float(
                    cost_calc.total_cost
                )

            # Store provider information
            usage_metric.detailed_metrics["provider"] = event.provider

            self.db.commit()

            logger.info(
                f"Recorded usage: {event.model_id} - {event.input_tokens}/{event.output_tokens} tokens - ${cost_calc.total_cost}"
            )

            return cost_calc

        except Exception as e:
            logger.error(f"Failed to record usage event: {e}", exc_info=True)
            self.db.rollback()
            raise

    async def get_usage_aggregates(
        self,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
    ) -> List[UsageAggregates]:
        """Get aggregated usage statistics."""

        query = self.db.query(ModelUsageMetrics)

        # Apply filters
        if model_id:
            query = query.filter(ModelUsageMetrics.model_id == model_id)

        if start_date:
            query = query.filter(ModelUsageMetrics.period_start >= start_date)

        if end_date:
            query = query.filter(ModelUsageMetrics.period_end <= end_date)

        # Filter by provider if specified
        if provider:
            query = query.filter(
                ModelUsageMetrics.detailed_metrics.op("->>")('"provider"') == provider
            )

        # Filter by user if specified
        if user_id:
            user_key = f"user_{user_id}"
            query = query.filter(ModelUsageMetrics.detailed_metrics.has_key(user_key))

        metrics = query.order_by(desc(ModelUsageMetrics.period_start)).all()

        aggregates = []
        for metric in metrics:
            aggregate = UsageAggregates(
                model_id=metric.model_id,
                period_start=metric.period_start,
                period_end=metric.period_end,
                total_requests=metric.total_requests,
                total_input_tokens=metric.total_tokens_input,
                total_output_tokens=metric.total_tokens_output,
                total_cost=Decimal(str(metric.total_cost)),
                avg_response_time_ms=metric.avg_response_time_ms,
                success_rate=metric.success_rate,
                avg_user_rating=metric.avg_user_rating,
                detailed_metrics=metric.detailed_metrics or {},
            )
            aggregates.append(aggregate)

        return aggregates

    async def get_cost_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get cost summary for specified period."""

        # Default to last 30 days if no dates specified
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        query = self.db.query(ModelUsageMetrics).filter(
            ModelUsageMetrics.period_start >= start_date,
            ModelUsageMetrics.period_end <= end_date,
        )

        # Filter by user if specified
        if user_id:
            user_key = f"user_{user_id}"
            query = query.filter(ModelUsageMetrics.detailed_metrics.has_key(user_key))

        metrics = query.all()

        # Calculate totals
        total_cost = sum(metric.total_cost for metric in metrics)
        total_requests = sum(metric.total_requests for metric in metrics)
        total_tokens = sum(
            metric.total_tokens_input + metric.total_tokens_output for metric in metrics
        )

        # Calculate costs by model
        model_costs = {}
        for metric in metrics:
            model_id = metric.model_id
            if model_id not in model_costs:
                model_costs[model_id] = {
                    "cost": 0.0,
                    "requests": 0,
                    "tokens": 0,
                    "provider": metric.detailed_metrics.get("provider", "unknown"),
                }

            model_costs[model_id]["cost"] += metric.total_cost
            model_costs[model_id]["requests"] += metric.total_requests
            model_costs[model_id]["tokens"] += (
                metric.total_tokens_input + metric.total_tokens_output
            )

        # Calculate costs by feature
        feature_costs = {}
        for metric in metrics:
            for key, value in (metric.detailed_metrics or {}).items():
                if key.startswith("feature_"):
                    feature_name = key.replace("feature_", "")
                    if feature_name not in feature_costs:
                        feature_costs[feature_name] = {"cost": 0.0, "requests": 0}
                    feature_costs[feature_name]["cost"] += value.get("cost", 0)
                    feature_costs[feature_name]["requests"] += value.get("requests", 0)

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "totals": {
                "cost": round(total_cost, 4),
                "requests": total_requests,
                "tokens": total_tokens,
                "avg_cost_per_request": round(total_cost / max(total_requests, 1), 4),
                "avg_cost_per_token": round(total_cost / max(total_tokens, 1), 6),
            },
            "by_model": model_costs,
            "by_feature": feature_costs,
            "currency": "USD",
        }

    async def get_real_time_usage(self) -> Dict[str, Any]:
        """Get real-time usage statistics for the current hour."""

        now = datetime.now(timezone.utc)
        period_start = now.replace(minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(hours=1)

        metrics = (
            self.db.query(ModelUsageMetrics)
            .filter(
                ModelUsageMetrics.period_start == period_start,
                ModelUsageMetrics.period_end == period_end,
            )
            .all()
        )

        current_hour_cost = sum(metric.total_cost for metric in metrics)
        current_hour_requests = sum(metric.total_requests for metric in metrics)

        # Get yesterday's same hour for comparison
        yesterday_period_start = period_start - timedelta(days=1)
        yesterday_period_end = period_end - timedelta(days=1)

        yesterday_metrics = (
            self.db.query(ModelUsageMetrics)
            .filter(
                ModelUsageMetrics.period_start == yesterday_period_start,
                ModelUsageMetrics.period_end == yesterday_period_end,
            )
            .all()
        )

        yesterday_cost = sum(metric.total_cost for metric in yesterday_metrics)
        yesterday_requests = sum(metric.total_requests for metric in yesterday_metrics)

        # Calculate percentage changes
        cost_change = 0.0
        if yesterday_cost > 0:
            cost_change = ((current_hour_cost - yesterday_cost) / yesterday_cost) * 100

        request_change = 0.0
        if yesterday_requests > 0:
            request_change = (
                (current_hour_requests - yesterday_requests) / yesterday_requests
            ) * 100

        return {
            "current_hour": {
                "cost": round(current_hour_cost, 4),
                "requests": current_hour_requests,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            },
            "yesterday_same_hour": {
                "cost": round(yesterday_cost, 4),
                "requests": yesterday_requests,
            },
            "changes": {
                "cost_change_percent": round(cost_change, 2),
                "request_change_percent": round(request_change, 2),
            },
            "currency": "USD",
        }

    @asynccontextmanager
    async def track_usage(
        self,
        model_id: str,
        provider: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        feature: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for tracking usage with automatic event recording."""

        start_time = datetime.now(timezone.utc)

        try:
            yield

            # If we get here, the operation was successful
            end_time = datetime.now(timezone.utc)
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            # Note: This context manager sets up the tracking but doesn't record
            # the actual usage - that should be done by the caller with token counts

        except Exception as e:
            # Operation failed
            end_time = datetime.now(timezone.utc)
            response_time_ms = (end_time - start_time).total_seconds() * 1000

            # Log failed operation
            logger.warning(f"Tracked failed operation: {model_id} - {e}")

            # Re-raise the exception
            raise

    async def cleanup_old_metrics(self, days_to_keep: int = 90):
        """Clean up old usage metrics to prevent database bloat."""

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        deleted_count = (
            self.db.query(ModelUsageMetrics)
            .filter(ModelUsageMetrics.period_end < cutoff_date)
            .delete()
        )

        self.db.commit()

        logger.info(f"Cleaned up {deleted_count} old usage metrics records")

        return deleted_count
