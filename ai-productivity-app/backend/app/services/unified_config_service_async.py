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


# Helper removed to avoid FastAPI inspection issues


class UnifiedConfigServiceAsync:
    def __init__(self, db: AsyncSession):
        # NB: we need to create a synchronous session for the legacy service.
        # AsyncSession doesn't have a sync_session attribute, so we create one from the sync engine.
        from app.database import SessionLocal
        self._sync_db = SessionLocal()
        self._svc = UnifiedConfigService(self._sync_db)
        self._db = db
    
    def __del__(self):
        # Clean up sync session when the async service is destroyed
        if hasattr(self, '_sync_db'):
            try:
                self._sync_db.close()
            except Exception:
                pass

    # --------------------------------------------------------------------- #
    # READ helpers
    # --------------------------------------------------------------------- #
    async def get_configuration_snapshot(
        self,
    ) -> Tuple[UnifiedModelConfig, List[ModelInfo], Dict[str, Dict[str, Any]]]:
        loop = asyncio.get_running_loop()
        
        def _get_snapshot():
            return self._svc.get_configuration_snapshot()
        
        return await loop.run_in_executor(_executor, _get_snapshot)

    async def get_defaults(self) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        
        def _get_defaults():
            return self._svc.get_defaults()
        
        return await loop.run_in_executor(_executor, _get_defaults)

    async def get_available_models(
        self, provider: str | None = None, include_deprecated: bool = False
    ) -> List[ModelInfo]:
        loop = asyncio.get_running_loop()
        
        def _get_models():
            return self._svc.get_available_models(provider, include_deprecated)
        
        return await loop.run_in_executor(_executor, _get_models)

    async def get_model_info(self, model_id: str) -> ModelInfo | None:
        loop = asyncio.get_running_loop()
        
        def _get_model_info():
            return self._svc.get_model_info(model_id)
        
        return await loop.run_in_executor(_executor, _get_model_info)

    async def validate_verbose(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        
        def _validate():
            return self._svc.validate_verbose(payload)
        
        return await loop.run_in_executor(_executor, _validate)

    # --------------------------------------------------------------------- #
    # WRITE helpers
    # --------------------------------------------------------------------- #
    async def update_config(
        self, update: ConfigUpdate, *, updated_by: str
    ) -> UnifiedModelConfig:
        loop = asyncio.get_running_loop()
        
        def _update_config():
            return self._svc.update_config(update.dict(exclude_unset=True), updated_by)
        
        return await loop.run_in_executor(_executor, _update_config)

    async def batch_update(
        self, updates: List[ConfigUpdate], *, updated_by: str
    ) -> UnifiedModelConfig:
        # Convert pydantic models to plain dicts
        dict_updates = [u.dict(exclude_unset=True) for u in updates]
        loop = asyncio.get_running_loop()
        
        def _batch_update():
            return self._svc.batch_update(dict_updates, updated_by)
        
        return await loop.run_in_executor(_executor, _batch_update)
