"""
Models API schemas for model configuration and switching.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Model configuration settings."""
    model_id: str
    provider: str = Field(..., pattern=r"^(openai|anthropic|azure|local)$")
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(1000, ge=1, le=8000)
    top_p: Optional[float] = Field(1.0, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(0.0, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(0.0, ge=-2, le=2)
    stop_sequences: Optional[List[str]] = None
    system_prompt: Optional[str] = None
    custom_params: Optional[Dict[str, Any]] = None


class ModelSwitchRequest(BaseModel):
    """Model switching request."""
    model_id: str
    project_id: str
    context: Optional[str] = None
    preserve_history: Optional[bool] = True
    reason: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    name: str
    provider: str
    description: Optional[str] = None
    max_tokens: int
    context_window: int
    cost_per_token: Optional[float] = None
    capabilities: List[str]
    available: bool = True
    performance_tier: Optional[str] = Field(
        None, pattern=r"^(fast|balanced|powerful)$"
    )


class ModelMetrics(BaseModel):
    """Model performance metrics."""
    model_id: str
    average_response_time: float
    success_rate: float
    user_satisfaction: float
    total_requests: int
    cost_efficiency: Optional[float] = None
    last_updated: datetime


class ModelSwitchResponse(BaseModel):
    """Model switch response."""
    success: bool
    new_model_id: str
    config: ModelConfig
    switch_time: float
    preserved_context: bool = False
    message: Optional[str] = None


class ModelListResponse(BaseModel):
    """Available models list response."""
    models: List[ModelInfo]
    total_count: int
    recommended: Optional[List[str]] = None
    filters_applied: Optional[Dict[str, Any]] = None


class ModelConfigResponse(BaseModel):
    """Model configuration response."""
    config: ModelConfig
    metrics: Optional[ModelMetrics] = None
    recommendations: Optional[List[str]] = None
    last_modified: datetime


class ModelResponse(BaseModel):
    """Standard models API response."""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
