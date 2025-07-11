from __future__ import annotations

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.generation import UnifiedModelConfig, ConfigUpdate
from ._deps import get_service, CurrentAdmin, UnifiedConfigServiceAsync
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
    admin: CurrentAdmin,
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_service)],
) -> UnifiedModelConfig:
    """
    Partially updates the configuration.  Requires Admin privileges.
    """
    try:
        new_cfg = await service.update_config(update, updated_by=admin.username)
        await notify_llm_client(new_cfg)
        await broadcast_config_update(service, new_cfg, event_type="config_update")
        return new_cfg
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except SQLAlchemyError:
        logger.exception("Database error during config update")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception:
        logger.exception("Unexpected error during config update")
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.put("/batch", response_model=UnifiedModelConfig, summary="Batch update (atomic)")
async def batch_update(
    updates: List[ConfigUpdate],
    admin: CurrentAdmin,
    service: Annotated[UnifiedConfigServiceAsync, Depends(get_service)],
) -> UnifiedModelConfig:
    """
    Applies a list of updates in a single DB transaction.
    Rolls back automatically if any update fails.
    """
    try:
        new_cfg = await service.batch_update(updates, updated_by=admin.username)
        await notify_llm_client(new_cfg)
        await broadcast_config_update(service, new_cfg, event_type="config_batch_update")
        return new_cfg
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Batch update failed")
        raise HTTPException(status_code=500, detail="Failed to batch-update configuration")

# Conflict-resolution or other write-level endpoints can also live here.
