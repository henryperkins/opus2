from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.generation import (
    UnifiedModelConfig,
    ConfigResponse,
    ModelInfo,
)
from ._deps import get_config_service, CurrentUser, UnifiedConfigServiceAsync

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/ai-config",
    tags=["AI Configuration – Read"],
    responses={500: {"description": "Internal Server Error"}},
)


# --------------------------------------------------------------------------- #
# Read-only endpoints
# --------------------------------------------------------------------------- #
@router.get("/test", summary="Test endpoint")
async def test_endpoint() -> dict:
    """Simple test endpoint without dependencies."""
    return {"status": "ok", "message": "test endpoint working"}

@router.get("", summary="Current configuration")
async def get_configuration() -> dict:
    """
    Returns the active configuration plus provider/model catalogue.
    """
    return {"status": "temporary", "message": "endpoint temporarily simplified"}


@router.get("/defaults", response_model=dict, summary="Built-in defaults")
async def get_defaults(
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_service)]
) -> Dict[str, Any]:
    return await service.get_defaults()


@router.get("/models", response_model=list[ModelInfo], summary="Available models")
async def list_models(
    current_user: CurrentUser,
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_config_service)],
    provider: Optional[str] = None,
    include_deprecated: bool = False,
) -> List[ModelInfo]:
    return await service.get_available_models(provider, include_deprecated)


@router.get("/models/{model_id}", response_model=ModelInfo, summary="Model details")
async def get_model(
    model_id: str,
    current_user: CurrentUser,
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_config_service)],
) -> ModelInfo:
    model = await service.get_model_info(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return model


@router.post("/validate", summary="Validate configuration (dry-run)")
async def validate_configuration(
    payload: Dict[str, Any],
    current_user: CurrentUser,
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_config_service)],
) -> Dict[str, Any]:
    return await service.validate_verbose(payload)

# Additional read-only endpoints (presets, test-run, etc.) can be migrated
# here following the same pattern.
