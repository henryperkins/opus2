from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.schemas.generation import ConfigResponse, ModelInfo
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

@router.get(
    "",
    summary="Current configuration",
    response_model=ConfigResponse,
)
async def get_configuration(
    current_user: CurrentUser,
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_config_service)],
) -> ConfigResponse:
    """Return the current unified configuration together with the full model
    catalogue and provider metadata.

    This endpoint is consumed by the front-end which expects the JSON
    structure below (camelCase keys thanks to the *CamelModel* base class):

        {
          "current": { … },
          "availableModels": [ … ],
          "providers": { … },
          "lastUpdated": "2025-05-18T12:34:56Z"
        }
    """

    try:
        current_cfg, available_models, providers = (
            await service.get_configuration_snapshot()
        )

        return ConfigResponse(
            current=current_cfg,
            available_models=available_models,
            providers=providers,
            last_updated=datetime.utcnow(),
        )
    except Exception as e:
        logger.warning(f"Failed to get configuration snapshot: {e}")

        # Try to provide defaults as fallback
        try:
            defaults = await service.get_defaults()
            available_models = await service.get_available_models() or []
            providers = await service.get_providers() or {}

            return ConfigResponse(
                current=defaults,
                available_models=available_models,
                providers=providers,
                last_updated=datetime.utcnow(),
                message=f"Configuration error: {str(e)}. Using default values.",
            )
        except Exception as fallback_error:
            logger.error(f"Failed to get defaults as fallback: {fallback_error}")

            # Return minimal working configuration
            minimal_config = {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 2048,
                "is_active": False
            }

            return ConfigResponse(
                current=minimal_config,
                available_models=[],
                providers={},
                last_updated=datetime.utcnow(),
                message="Configuration error. Using minimal fallback configuration.",
            )


@router.get("/defaults", response_model=dict, summary="Built-in defaults")
async def get_defaults(
    service: Annotated[
        UnifiedConfigServiceAsync, Depends(get_config_service)
    ],
) -> Dict[str, Any]:
    """Return the built-in default configuration values."""
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


# --------------------------------------------------------------------------- #
# Test helper (legacy alias)
# --------------------------------------------------------------------------- #

from fastapi import Request


@router.post("/test", summary="Validate configuration (simple response)")
async def test_configuration(
    request: Request,
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_config_service)],
):
    """Legacy helper expected by older front-end code (POST /test).

    Accepts *both* ``application/json`` and
    ``application/x-www-form-urlencoded`` bodies because the original React
    client occasionally falls back to URL-encoded payloads when Axios is
    handed a plain object without an explicit ``headers`` override.
    """

    # -------------------------------------------------------------------
    # Robust payload extraction – support JSON **and** form-urlencoded.
    # -------------------------------------------------------------------
    ctype = request.headers.get("content-type", "").split(";")[0]

    if ctype == "application/json":
        payload: Dict[str, Any] = await request.json()
    elif ctype == "application/x-www-form-urlencoded":
        form = await request.form()
        payload = dict(form)  # ImmutableMultiDict → plain dict
    else:  # pragma: no cover – should not happen
        payload = {}

    # Parse simple numeric fields that arrive as strings via form-urlenc
    numeric_fields = (
        "temperature",
        "max_tokens",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
    )
    for fld in numeric_fields:
        if fld in payload and isinstance(payload[fld], str):
            try:
                payload[fld] = float(payload[fld]) if "." in payload[fld] else int(payload[fld])
            except ValueError:
                pass

    import time

    start = time.monotonic()
    res = await service.validate_verbose(payload)
    latency_ms = int((time.monotonic() - start) * 1000)

    return {
        "success": res.get("valid", False),
        "message": None if res.get("valid") else res.get("error"),
        "latency": latency_ms,
        "error": None if res.get("valid") else res.get("error"),
    }


# --------------------------------------------------------------------------- #
# Presets
# --------------------------------------------------------------------------- #

@router.get(
    "/presets",
    summary="Configuration presets",
    response_class=JSONResponse,
)
async def list_presets(
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_config_service)],
):
    """Return predefined configuration presets without Pydantic validation."""
    presets = await service.get_presets()
    return JSONResponse(content=presets)

# Additional read-only endpoints (presets, test-run, etc.) can be migrated
# here following the same pattern.
