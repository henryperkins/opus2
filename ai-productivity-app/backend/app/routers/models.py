"""
Models API router for model configuration and switching.

NOTE: This router is being phased out in favor of the unified config system.
The endpoints here redirect to or integrate with /api/config endpoints to
avoid duplication and ensure consistency.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
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
from ..services.config_service import ConfigService

router = APIRouter(prefix="/api/v1/models", tags=["models"])

# Deprecation warning for old endpoints
DEPRECATION_WARNING = {
    "warning": "This endpoint is deprecated. Please use /api/config endpoints instead.",
    "migration_guide": {
        "GET /api/v1/models/available": "GET /api/config",
        "POST /api/v1/models/switch": "PUT /api/config/model",
        "GET /api/v1/models/config/{model_id}": "GET /api/config",
        "PUT /api/v1/models/config/{model_id}": "PUT /api/config/model"
    }
}


@router.get("/available")
async def get_available_models(
    provider: Optional[str] = None,
    performance_tier: Optional[str] = None,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Get list of available models.
    
    DEPRECATED: Please use GET /api/config instead.
    """
    # Return deprecation warning with redirect info
    return ModelResponse(
        success=True,
        data={
            **DEPRECATION_WARNING,
            "redirect_to": "/api/config",
            "status": "deprecated"
        }
    )


@router.post("/switch")
async def switch_model(
    request: ModelSwitchRequest,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Switch to a different model configuration.
    
    DEPRECATED: Please use PUT /api/config/model instead.
    """
    try:
        # Integrate with real config system
        config_service = ConfigService(db)
        
        # Update configuration using the real system
        update_data = {
            "chat_model": request.model_id,
            "provider": "openai" if "gpt" in request.model_id.lower() else "azure"
        }
        
        config_service.set_multiple_config(update_data, updated_by="models_api_deprecated")
        
        # Trigger LLM client reconfiguration
        try:
            from app.llm.client import llm_client
            await llm_client.reconfigure(
                provider=update_data.get("provider"),
                model=update_data.get("chat_model")
            )
        except Exception as e:
            # Log but don't fail the response
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Failed to reconfigure LLM client in deprecated endpoint: %s", e)
        
        return ModelResponse(
            success=True,
            data={
                **DEPRECATION_WARNING,
                "redirect_to": "/api/config/model",
                "status": "deprecated",
                "action_completed": True,
                "message": f"Model switched to {request.model_id} via deprecated endpoint"
            }
        )
    except Exception as e:
        detail = f"Failed to switch model: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/config/{model_id}")
async def get_model_config(
    model_id: str,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Get configuration for a specific model.
    
    DEPRECATED: Please use GET /api/config instead.
    """
    return ModelResponse(
        success=True,
        data={
            **DEPRECATION_WARNING,
            "redirect_to": "/api/config",
            "status": "deprecated",
            "requested_model": model_id
        }
    )


@router.put("/config/{model_id}")
async def update_model_config(
    model_id: str,
    config: ModelConfig,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Update configuration for a specific model.
    
    DEPRECATED: Please use PUT /api/config/model instead.
    """
    return ModelResponse(
        success=True,
        data={
            **DEPRECATION_WARNING,
            "redirect_to": "/api/config/model",
            "status": "deprecated",
            "requested_model": model_id
        }
    )


@router.get("/metrics/{model_id}")
async def get_model_metrics(
    model_id: str,
    days: Optional[int] = 7,
    db: Session = Depends(get_db)
) -> ModelResponse:
    """Get performance metrics for a specific model.
    
    NOTE: Metrics functionality not yet implemented in the new config system.
    """
    return ModelResponse(
        success=True,
        data={
            **DEPRECATION_WARNING,
            "status": "not_implemented",
            "message": "Metrics functionality will be added to the new config system in a future update",
            "requested_model": model_id,
            "requested_days": days
        }
    )
