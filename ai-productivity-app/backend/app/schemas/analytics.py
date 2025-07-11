"""
Analytics API schemas for metrics tracking and reporting.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class QualityMetrics(BaseModel):
    """Quality metrics for response tracking."""

    response_id: str
    project_id: str
    accuracy: Optional[float] = Field(None, ge=0, le=1)
    relevance: Optional[float] = Field(None, ge=0, le=1)
    completeness: Optional[float] = Field(None, ge=0, le=1)
    clarity: Optional[float] = Field(None, ge=0, le=1)
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    response_time: Optional[float] = Field(None, ge=0)
    timestamp: Optional[datetime] = None


class UserFeedback(BaseModel):
    """User feedback on responses."""

    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = None
    helpful: Optional[bool] = None
    categories: Optional[List[str]] = None
    user_id: Optional[str] = None
    timestamp: Optional[datetime] = None


class FlowMetrics(BaseModel):
    """Metrics for chat flow execution."""

    project_id: str
    flow_type: str = Field(..., pattern=r"^(knowledge|model|rendering)$")
    success: bool
    response_time: Optional[float] = Field(None, ge=0)
    knowledge_hit: Optional[bool] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class InteractionData(BaseModel):
    """User interaction with interactive elements."""

    project_id: str
    element_type: str
    action: str
    element_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class TimeRange(BaseModel):
    """Time range for analytics queries."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period: Optional[str] = Field(None, pattern=r"^(hour|day|week|month|year)$")


class DashboardMetrics(BaseModel):
    """Dashboard metrics response."""

    total_requests: int
    successful_requests: int
    average_response_time: float
    knowledge_hit_rate: float
    user_satisfaction: float
    popular_flows: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
    quality_trends: Dict[str, List[float]]


class AnalyticsResponse(BaseModel):
    """Standard analytics response."""

    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
