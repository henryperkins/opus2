"""
Helper utilities used by read.py and write.py.
"""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Dict, Any, List

from app.websocket.manager import connection_manager
from app.schemas.generation import UnifiedModelConfig
from app.services.unified_config_service_async import UnifiedConfigServiceAsync

logger = logging.getLogger(__name__)


async def notify_llm_client(cfg: UnifiedModelConfig) -> None:
    """
    Push the updated configuration to the in-process LLM client
    so that subsequent requests use the new settings.
    """
    try:
        from app.llm.client import llm_client

        await llm_client.reconfigure(**cfg.model_dump())
    except Exception:  # pragma: no cover
        logger.warning("LLM client re-configuration failed", exc_info=True)


async def broadcast_config_update(
    service: UnifiedConfigServiceAsync,
    cfg: UnifiedModelConfig,
    event_type: str = "config_update",
) -> None:
    """
    Broadcast the latest configuration to all connected WebSocket clients.
    """
    try:
        message: Dict[str, Any] = {
            "type": event_type,
            "data": {
                "current": cfg.model_dump(by_alias=True),
                "available_models": [
                    m.model_dump(by_alias=True)
                    for m in await service.get_available_models()
                ],
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        await connection_manager.broadcast_config_update(message)
    except Exception:  # pragma: no cover
        logger.warning("WebSocket broadcast failed", exc_info=True)
