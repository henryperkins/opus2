from __future__ import annotations

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.generation import UnifiedModelConfig, ConfigUpdate
from ._deps import get_config_service, CurrentUser, UnifiedConfigServiceAsync
from ._helpers import notify_llm_client, broadcast_config_update

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/ai-config",
    tags=["AI Configuration – Write"],
    responses={500: {"description": "Internal Server Error"}},
)


# --------------------------------------------------------------------------- #
# Mutating endpoints (Admin only)
# --------------------------------------------------------------------------- #
@router.patch("", response_model=UnifiedModelConfig, summary="Partial update")
async def update_config(
    update: ConfigUpdate,
    user: CurrentUser,
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_config_service)],
) -> UnifiedModelConfig:
    """
    Partially updates the configuration.  Requires authentication.
    """
    try:
        # Log the incoming update for debugging
        logger.info(f"Received config update from {user.username}: {update.dict(exclude_unset=True)}")

        new_cfg = await service.update_config(update, updated_by=user.username)
        await notify_llm_client(new_cfg)
        await broadcast_config_update(service, new_cfg, event_type="config_update")
        return new_cfg
    except ValueError as e:
        logger.error(f"Validation error during config update: {str(e)}")
        # Provide detailed error information for frontend
        error_msg = str(e)
        if hasattr(e, "errors"):
            # Pydantic v2: include field errors if present
            field_errors = getattr(e, "errors", lambda: [])()
            if field_errors:
                error_msg += " | " + "; ".join(
                    f"{err.get('loc', [''])[0]}: {err.get('msg', '')}" for err in field_errors
                )
        if "Field required" in error_msg:
            error_msg = "Missing required fields. Please ensure both 'provider' and 'modelId' are included in the configuration."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg)
    except SQLAlchemyError:
        logger.exception("Database error during config update")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception:
        logger.exception("Unexpected error during config update")
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.put("/batch", response_model=UnifiedModelConfig, summary="Batch update (atomic)")
async def batch_update(
    updates: List[ConfigUpdate],
    user: CurrentUser,
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_config_service)],
) -> UnifiedModelConfig:
    """
    Applies a list of updates in a single DB transaction.
    Rolls back automatically if any update fails.
    """
    try:
        new_cfg = await service.batch_update(updates, updated_by=user.username)
        await notify_llm_client(new_cfg)
        await broadcast_config_update(service, new_cfg, event_type="config_batch_update")
        return new_cfg
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Batch update failed")
        raise HTTPException(status_code=500, detail="Failed to batch-update configuration")

# Conflict-resolution or other write-level endpoints can also live here.
