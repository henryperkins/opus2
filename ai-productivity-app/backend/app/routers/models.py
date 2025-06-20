"""
Models API router for model configuration and switching.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.models import (
    ModelConfig,
    ModelSwitchRequest,
    ModelInfo,
    ModelMetrics,
    ModelSwitchResponse,
    ModelListResponse,
    ModelConfigResponse,
    ModelResponse
)

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("/available")
async def get_available_models(
    provider: Optional[str] = None,
    performance_tier: Optional[str] = None,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Get list of available models."""
    try:
        # Mock available models
        mock_models = [
            ModelInfo(
                id="gpt-4",
                name="GPT-4",
                provider="openai",
                description="Most capable GPT model",
                max_tokens=4096,
                context_window=8192,
                cost_per_token=0.03,
                capabilities=["text", "code", "reasoning"],
                performance_tier="powerful"
            ),
            ModelInfo(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider="openai",
                description="Fast and efficient model",
                max_tokens=4096,
                context_window=4096,
                cost_per_token=0.002,
                capabilities=["text", "code"],
                performance_tier="fast"
            ),
            ModelInfo(
                id="claude-3",
                name="Claude 3",
                provider="anthropic",
                description="Anthropic's latest model",
                max_tokens=4096,
                context_window=100000,
                cost_per_token=0.025,
                capabilities=["text", "code", "analysis"],
                performance_tier="balanced"
            )
        ]

        # Apply filters
        filtered_models = mock_models
        if provider:
            filtered_models = [
                m for m in filtered_models if m.provider == provider
            ]
        if performance_tier:
            filtered_models = [
                m for m in filtered_models
                if m.performance_tier == performance_tier
            ]

        response_data = ModelListResponse(
            models=filtered_models,
            total_count=len(filtered_models),
            recommended=["gpt-4", "claude-3"]
        )

        return ModelResponse(success=True, data=response_data.dict())
    except Exception as e:
        detail = f"Failed to get available models: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/switch")
async def switch_model(
    request: ModelSwitchRequest,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Switch to a different model configuration."""
    try:
        # Mock model switching logic
        start_time = datetime.utcnow()

        # Simulate model configuration
        new_config = ModelConfig(
            model_id=request.model_id,
            provider="openai" if "gpt" in request.model_id else "anthropic",
            temperature=0.7,
            max_tokens=2000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )

        switch_time = (datetime.utcnow() - start_time).total_seconds()

        response_data = ModelSwitchResponse(
            success=True,
            new_model_id=request.model_id,
            config=new_config,
            switch_time=switch_time,
            preserved_context=request.preserve_history,
            message=f"Successfully switched to {request.model_id}"
        )

        return ModelResponse(success=True, data=response_data.dict())
    except Exception as e:
        detail = f"Failed to switch model: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/config/{model_id}")
async def get_model_config(
    model_id: str,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Get configuration for a specific model."""
    try:
        # Mock model configuration
        config = ModelConfig(
            model_id=model_id,
            provider="openai" if "gpt" in model_id else "anthropic",
            temperature=0.7,
            max_tokens=2000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            system_prompt="You are a helpful AI assistant."
        )

        # Mock metrics
        metrics = ModelMetrics(
            model_id=model_id,
            average_response_time=1.2,
            success_rate=0.95,
            user_satisfaction=4.3,
            total_requests=542,
            cost_efficiency=0.85,
            last_updated=datetime.utcnow()
        )

        response_data = ModelConfigResponse(
            config=config,
            metrics=metrics,
            recommendations=[
                "Consider lowering temperature for more consistent outputs",
                "Increase max_tokens for longer responses"
            ],
            last_modified=datetime.utcnow()
        )

        return ModelResponse(success=True, data=response_data.dict())
    except Exception as e:
        detail = f"Failed to get model config: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.put("/config/{model_id}")
async def update_model_config(
    model_id: str,
    config: ModelConfig,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Update configuration for a specific model."""
    try:
        # Mock configuration update
        # In production, this would validate and store the configuration

        # Ensure model_id matches
        if config.model_id != model_id:
            config.model_id = model_id

        return ModelResponse(
            success=True,
            message=f"Configuration updated for {model_id}",
            data={"config": config.dict(), "updated_at": datetime.utcnow()}
        )
    except Exception as e:
        detail = f"Failed to update model config: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/metrics/{model_id}")
async def get_model_metrics(
    model_id: str,
    days: Optional[int] = 7,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Get performance metrics for a specific model."""
    try:
        # Mock metrics data
        metrics = ModelMetrics(
            model_id=model_id,
            average_response_time=1.2,
            success_rate=0.95,
            user_satisfaction=4.3,
            total_requests=542,
            cost_efficiency=0.85,
            last_updated=datetime.utcnow()
        )

        # Mock trend data
        trend_data = {
            "response_times": [1.1, 1.3, 1.2, 1.0, 1.2, 1.1, 1.2],
            "success_rates": [0.94, 0.96, 0.95, 0.97, 0.95, 0.94, 0.95],
            "satisfaction_scores": [4.2, 4.4, 4.3, 4.5, 4.3, 4.2, 4.3]
        }

        response_data = {
            "metrics": metrics.dict(),
            "trends": trend_data,
            "period_days": days
        }

        return ModelResponse(success=True, data=response_data)
    except Exception as e:
        detail = f"Failed to get model metrics: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)
