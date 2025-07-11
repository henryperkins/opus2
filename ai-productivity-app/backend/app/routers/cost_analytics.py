"""Cost analytics API endpoints for LLM usage monitoring and reporting."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.services.cost_tracking import CostTrackingService, UsageAggregates
from app.dependencies import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cost-analytics", tags=["cost_analytics"])


# Response schemas
class CostSummaryResponse(BaseModel):
    """Cost summary response."""

    period: Dict[str, str]
    totals: Dict[str, Any]
    by_model: Dict[str, Any]
    by_feature: Dict[str, Any]
    currency: str = "USD"


class UsageMetricsResponse(BaseModel):
    """Usage metrics response."""

    model_id: str
    period_start: datetime
    period_end: datetime
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: Decimal
    avg_response_time_ms: Optional[float] = None
    success_rate: Optional[float] = None
    avg_user_rating: Optional[float] = None
    detailed_metrics: Dict[str, Any] = Field(default_factory=dict)


class RealTimeUsageResponse(BaseModel):
    """Real-time usage response."""

    current_hour: Dict[str, Any]
    yesterday_same_hour: Dict[str, Any]
    changes: Dict[str, float]
    currency: str = "USD"


class CostTrendsResponse(BaseModel):
    """Cost trends response."""

    period: str
    data_points: List[Dict[str, Any]]
    total_cost: Decimal
    avg_daily_cost: Decimal
    peak_usage_day: Optional[str] = None
    currency: str = "USD"


class ModelComparisonResponse(BaseModel):
    """Model comparison response."""

    models: List[Dict[str, Any]]
    time_period: Dict[str, str]
    comparison_metrics: Dict[str, Any]
    currency: str = "USD"


class UserUsageResponse(BaseModel):
    """User usage response."""

    user_id: int
    username: Optional[str] = None
    total_cost: Decimal
    total_requests: int
    total_tokens: int
    avg_cost_per_request: Decimal
    top_models: List[Dict[str, Any]]
    top_features: List[Dict[str, Any]]
    currency: str = "USD"


# API endpoints
@router.get("/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    start_date: Optional[datetime] = Query(None, description="Start date for analysis"),
    end_date: Optional[datetime] = Query(None, description="End date for analysis"),
    user_id: Optional[int] = Query(None, description="Filter by specific user"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get cost summary for specified period."""

    # If user_id is specified and current user is not admin, only allow their own data
    if user_id and current_user and current_user.id != user_id:
        # Check if current user has admin privileges
        if not getattr(current_user, "is_admin", False):
            raise HTTPException(
                status_code=403,
                detail="Access denied: can only view your own usage data",
            )

    # If no user_id specified and user is not admin, filter by their own data
    if not user_id and current_user and not getattr(current_user, "is_admin", False):
        user_id = current_user.id

    cost_tracking_service = CostTrackingService(db)

    try:
        summary = await cost_tracking_service.get_cost_summary(
            start_date=start_date, end_date=end_date, user_id=user_id
        )

        return CostSummaryResponse(**summary)

    except Exception as e:
        logger.error(f"Error getting cost summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cost summary")


@router.get("/usage", response_model=List[UsageMetricsResponse])
async def get_usage_metrics(
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get detailed usage metrics."""

    # Apply access control
    if user_id and current_user and current_user.id != user_id:
        if not getattr(current_user, "is_admin", False):
            raise HTTPException(
                status_code=403,
                detail="Access denied: can only view your own usage data",
            )

    if not user_id and current_user and not getattr(current_user, "is_admin", False):
        user_id = current_user.id

    cost_tracking_service = CostTrackingService(db)

    try:
        aggregates = await cost_tracking_service.get_usage_aggregates(
            model_id=model_id,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
        )

        # Limit results
        aggregates = aggregates[:limit]

        return [
            UsageMetricsResponse(
                model_id=agg.model_id,
                period_start=agg.period_start,
                period_end=agg.period_end,
                total_requests=agg.total_requests,
                total_input_tokens=agg.total_input_tokens,
                total_output_tokens=agg.total_output_tokens,
                total_cost=agg.total_cost,
                avg_response_time_ms=agg.avg_response_time_ms,
                success_rate=agg.success_rate,
                avg_user_rating=agg.avg_user_rating,
                detailed_metrics=agg.detailed_metrics,
            )
            for agg in aggregates
        ]

    except Exception as e:
        logger.error(f"Error getting usage metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve usage metrics")


@router.get("/real-time", response_model=RealTimeUsageResponse)
async def get_real_time_usage(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get real-time usage statistics for the current hour."""

    cost_tracking_service = CostTrackingService(db)

    try:
        usage_data = await cost_tracking_service.get_real_time_usage()
        return RealTimeUsageResponse(**usage_data)

    except Exception as e:
        logger.error(f"Error getting real-time usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve real-time usage"
        )


@router.get("/trends", response_model=CostTrendsResponse)
async def get_cost_trends(
    period: str = Query("7d", regex="^(24h|7d|30d|90d)$", description="Time period"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Get cost trends over time."""

    # Apply access control
    if user_id and current_user and current_user.id != user_id:
        if not getattr(current_user, "is_admin", False):
            raise HTTPException(
                status_code=403,
                detail="Access denied: can only view your own usage data",
            )

    if not user_id and current_user and not getattr(current_user, "is_admin", False):
        user_id = current_user.id

    # Calculate date range based on period
    end_date = datetime.now(timezone.utc)
    period_days = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    start_date = end_date - timedelta(days=period_days[period])

    cost_tracking_service = CostTrackingService(db)

    try:
        # Get aggregated data
        aggregates = await cost_tracking_service.get_usage_aggregates(
            start_date=start_date, end_date=end_date, user_id=user_id
        )

        # Group by day and calculate trends
        daily_costs = {}
        for agg in aggregates:
            day = agg.period_start.date().isoformat()
            if day not in daily_costs:
                daily_costs[day] = {
                    "date": day,
                    "cost": Decimal("0.00"),
                    "requests": 0,
                    "tokens": 0,
                }
            daily_costs[day]["cost"] += agg.total_cost
            daily_costs[day]["requests"] += agg.total_requests
            daily_costs[day]["tokens"] += (
                agg.total_input_tokens + agg.total_output_tokens
            )

        # Sort by date
        data_points = sorted(daily_costs.values(), key=lambda x: x["date"])

        # Calculate metrics
        total_cost = sum(point["cost"] for point in data_points)
        avg_daily_cost = (
            total_cost / len(data_points) if data_points else Decimal("0.00")
        )

        # Find peak usage day
        peak_usage_day = None
        if data_points:
            peak_day = max(data_points, key=lambda x: x["cost"])
            peak_usage_day = peak_day["date"]

        return CostTrendsResponse(
            period=period,
            data_points=data_points,
            total_cost=total_cost,
            avg_daily_cost=avg_daily_cost,
            peak_usage_day=peak_usage_day,
            currency="USD",
        )

    except Exception as e:
        logger.error(f"Error getting cost trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cost trends")


@router.get("/models/comparison", response_model=ModelComparisonResponse)
async def get_model_comparison(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Compare usage and costs across different models."""

    # Apply access control
    if user_id and current_user and current_user.id != user_id:
        if not getattr(current_user, "is_admin", False):
            raise HTTPException(
                status_code=403,
                detail="Access denied: can only view your own usage data",
            )

    if not user_id and current_user and not getattr(current_user, "is_admin", False):
        user_id = current_user.id

    cost_tracking_service = CostTrackingService(db)

    try:
        # Get usage aggregates
        aggregates = await cost_tracking_service.get_usage_aggregates(
            start_date=start_date, end_date=end_date, user_id=user_id
        )

        # Group by model
        model_stats = {}
        for agg in aggregates:
            model_id = agg.model_id
            if model_id not in model_stats:
                model_stats[model_id] = {
                    "model_id": model_id,
                    "total_cost": Decimal("0.00"),
                    "total_requests": 0,
                    "total_tokens": 0,
                    "avg_response_time_ms": 0,
                    "success_rate": 0,
                    "response_times": [],
                    "success_rates": [],
                }

            stats = model_stats[model_id]
            stats["total_cost"] += agg.total_cost
            stats["total_requests"] += agg.total_requests
            stats["total_tokens"] += agg.total_input_tokens + agg.total_output_tokens

            if agg.avg_response_time_ms:
                stats["response_times"].append(agg.avg_response_time_ms)
            if agg.success_rate is not None:
                stats["success_rates"].append(agg.success_rate)

        # Calculate averages
        for model_id, stats in model_stats.items():
            if stats["response_times"]:
                stats["avg_response_time_ms"] = sum(stats["response_times"]) / len(
                    stats["response_times"]
                )
            if stats["success_rates"]:
                stats["success_rate"] = sum(stats["success_rates"]) / len(
                    stats["success_rates"]
                )

            # Calculate derived metrics
            stats["avg_cost_per_request"] = (
                stats["total_cost"] / stats["total_requests"]
                if stats["total_requests"] > 0
                else Decimal("0.00")
            )
            stats["avg_cost_per_token"] = (
                stats["total_cost"] / stats["total_tokens"]
                if stats["total_tokens"] > 0
                else Decimal("0.00")
            )

            # Clean up temporary arrays
            del stats["response_times"]
            del stats["success_rates"]

        # Sort models by total cost
        models = sorted(
            model_stats.values(), key=lambda x: x["total_cost"], reverse=True
        )

        # Calculate comparison metrics
        total_cost = sum(model["total_cost"] for model in models)
        total_requests = sum(model["total_requests"] for model in models)
        most_expensive_model = models[0]["model_id"] if models else None
        most_used_model = (
            max(models, key=lambda x: x["total_requests"])["model_id"]
            if models
            else None
        )

        comparison_metrics = {
            "total_cost": total_cost,
            "total_requests": total_requests,
            "most_expensive_model": most_expensive_model,
            "most_used_model": most_used_model,
            "num_models": len(models),
        }

        time_period = {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        }

        return ModelComparisonResponse(
            models=models,
            time_period=time_period,
            comparison_metrics=comparison_metrics,
            currency="USD",
        )

    except Exception as e:
        logger.error(f"Error getting model comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve model comparison"
        )


@router.get("/users/{user_id}/usage", response_model=UserUsageResponse)
async def get_user_usage(
    user_id: int = Path(..., description="User ID"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed usage statistics for a specific user."""

    # Access control: users can only view their own data unless they're admin
    if current_user.id != user_id and not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=403, detail="Access denied: can only view your own usage data"
        )

    cost_tracking_service = CostTrackingService(db)

    try:
        # Get user info
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get usage aggregates for the user
        aggregates = await cost_tracking_service.get_usage_aggregates(
            start_date=start_date, end_date=end_date, user_id=user_id
        )

        # Calculate totals
        total_cost = sum(agg.total_cost for agg in aggregates)
        total_requests = sum(agg.total_requests for agg in aggregates)
        total_tokens = sum(
            agg.total_input_tokens + agg.total_output_tokens for agg in aggregates
        )
        avg_cost_per_request = (
            total_cost / total_requests if total_requests > 0 else Decimal("0.00")
        )

        # Calculate top models
        model_usage = {}
        for agg in aggregates:
            model_id = agg.model_id
            if model_id not in model_usage:
                model_usage[model_id] = {
                    "model_id": model_id,
                    "cost": Decimal("0.00"),
                    "requests": 0,
                }
            model_usage[model_id]["cost"] += agg.total_cost
            model_usage[model_id]["requests"] += agg.total_requests

        top_models = sorted(
            model_usage.values(), key=lambda x: x["cost"], reverse=True
        )[:5]

        # Calculate top features
        feature_usage = {}
        for agg in aggregates:
            for key, value in agg.detailed_metrics.items():
                if key.startswith("feature_"):
                    feature_name = key.replace("feature_", "")
                    if feature_name not in feature_usage:
                        feature_usage[feature_name] = {
                            "feature": feature_name,
                            "cost": 0.0,
                            "requests": 0,
                        }
                    feature_usage[feature_name]["cost"] += value.get("cost", 0)
                    feature_usage[feature_name]["requests"] += value.get("requests", 0)

        top_features = sorted(
            feature_usage.values(), key=lambda x: x["cost"], reverse=True
        )[:5]

        return UserUsageResponse(
            user_id=user_id,
            username=getattr(user, "username", None),
            total_cost=total_cost,
            total_requests=total_requests,
            total_tokens=total_tokens,
            avg_cost_per_request=avg_cost_per_request,
            top_models=top_models,
            top_features=top_features,
            currency="USD",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user usage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve user usage")


@router.post("/cleanup")
async def cleanup_old_metrics(
    days_to_keep: int = Query(90, ge=1, le=365, description="Number of days to keep"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clean up old usage metrics (admin only)."""

    # Check if user is admin
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=403, detail="Access denied: admin privileges required"
        )

    cost_tracking_service = CostTrackingService(db)

    try:
        deleted_count = await cost_tracking_service.cleanup_old_metrics(days_to_keep)

        return {
            "message": f"Successfully cleaned up {deleted_count} old usage metrics",
            "days_kept": days_to_keep,
            "deleted_records": deleted_count,
        }

    except Exception as e:
        logger.error(f"Error cleaning up metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cleanup old metrics")


@router.get("/export")
async def export_usage_data(
    format: str = Query("csv", regex="^(csv|json)$", description="Export format"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export usage data in various formats."""

    # Access control
    if user_id and current_user.id != user_id:
        if not getattr(current_user, "is_admin", False):
            raise HTTPException(
                status_code=403,
                detail="Access denied: can only export your own usage data",
            )

    if not user_id and not getattr(current_user, "is_admin", False):
        user_id = current_user.id

    cost_tracking_service = CostTrackingService(db)

    try:
        # Get usage aggregates
        aggregates = await cost_tracking_service.get_usage_aggregates(
            start_date=start_date, end_date=end_date, user_id=user_id
        )

        if format == "csv":
            # Generate CSV
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "model_id",
                    "period_start",
                    "period_end",
                    "total_requests",
                    "total_input_tokens",
                    "total_output_tokens",
                    "total_cost",
                    "avg_response_time_ms",
                    "success_rate",
                ]
            )

            # Write data
            for agg in aggregates:
                writer.writerow(
                    [
                        agg.model_id,
                        agg.period_start.isoformat(),
                        agg.period_end.isoformat(),
                        agg.total_requests,
                        agg.total_input_tokens,
                        agg.total_output_tokens,
                        float(agg.total_cost),
                        agg.avg_response_time_ms,
                        agg.success_rate,
                    ]
                )

            # Return CSV response
            from fastapi.responses import StreamingResponse

            output.seek(0)
            return StreamingResponse(
                io.StringIO(output.getvalue()),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=usage_data.csv"},
            )

        else:  # JSON format
            data = [
                {
                    "model_id": agg.model_id,
                    "period_start": agg.period_start.isoformat(),
                    "period_end": agg.period_end.isoformat(),
                    "total_requests": agg.total_requests,
                    "total_input_tokens": agg.total_input_tokens,
                    "total_output_tokens": agg.total_output_tokens,
                    "total_cost": float(agg.total_cost),
                    "avg_response_time_ms": agg.avg_response_time_ms,
                    "success_rate": agg.success_rate,
                    "detailed_metrics": agg.detailed_metrics,
                }
                for agg in aggregates
            ]

            return JSONResponse(content=data)

    except Exception as e:
        logger.error(f"Error exporting usage data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export usage data")
