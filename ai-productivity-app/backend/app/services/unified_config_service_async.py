"""
Async façade for the legacy synchronous UnifiedConfigService.

All heavy calls are executed inside a default ThreadPool so they do not
block the FastAPI event-loop.  Once you migrate to SQLAlchemy-async
properly, replace each `run_in_executor` with genuine async code.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.unified_config_service import UnifiedConfigService
from app.schemas.generation import (
    UnifiedModelConfig,
    ModelInfo,
    ConfigUpdate,
)

_executor = ThreadPoolExecutor()


def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return loop.run_in_executor(_executor, lambda: func(*args, **kwargs))


class UnifiedConfigServiceAsync:
    def __init__(self, db: AsyncSession):
        # NB: we pass the *sync* session object to the legacy service.
        # If you migrate to async SQLAlchemy, refactor the legacy service first.
        self._svc = UnifiedConfigService(db.sync_session)  # type: ignore[attr-defined]

    # --------------------------------------------------------------------- #
    # READ helpers
    # --------------------------------------------------------------------- #
    async def get_configuration_snapshot(
        self,
    ) -> Tuple[UnifiedModelConfig, List[ModelInfo], Dict[str, Dict[str, Any]]]:
        return await _run_sync(self._svc.get_configuration_snapshot)

    async def get_defaults(self) -> Dict[str, Any]:
        return await _run_sync(self._svc.get_defaults)

    async def get_available_models(
        self, provider: str | None = None, include_deprecated: bool = False
    ) -> List[ModelInfo]:
        return await _run_sync(self._svc.get_available_models, provider, include_deprecated)

    async def get_model_info(self, model_id: str) -> ModelInfo | None:
        return await _run_sync(self._svc.get_model_info, model_id)

    async def validate_verbose(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await _run_sync(self._svc.validate_verbose, payload)

    # --------------------------------------------------------------------- #
    # WRITE helpers
    # --------------------------------------------------------------------- #
    async def update_config(
        self, update: ConfigUpdate, *, updated_by: str
    ) -> UnifiedModelConfig:
        return await _run_sync(self._svc.update_config, update.dict(exclude_unset=True), updated_by)

    async def batch_update(
        self, updates: List[ConfigUpdate], *, updated_by: str
    ) -> UnifiedModelConfig:
        # Convert pydantic models to plain dicts
        dict_updates = [u.dict(exclude_unset=True) for u in updates]
        return await _run_sync(self._svc.batch_update, dict_updates, updated_by)
