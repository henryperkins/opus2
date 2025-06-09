"""Global WebSocket notification manager.


This manager is *user-centric* (not session-centric like chat).  Each browser
tab opens exactly **one** WebSocket connection to ``/ws/notify`` after login.
Backend tasks call ``notify_manager.send(user_id, payload)`` to push JSON
events.

The implementation is deliberately simple for MVP – we keep an *in-memory*
mapping.  When we later move to multi-process Gunicorn or external workers we
will introduce a Redis pub/sub backend behind the same interface.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotifyManager:  # noqa: D101 – simple container
    def __init__(self) -> None:
        self._connections: Dict[int, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int) -> None:  # noqa: D401
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(user_id, []).append(websocket)
        logger.debug("Notify ws connected for user %s (total=%s)", user_id, len(self._connections[user_id]))

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:  # noqa: D401
        async with self._lock:
            conns = self._connections.get(user_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                self._connections.pop(user_id, None)
        logger.debug("Notify ws disconnected for user %s", user_id)

    async def send(self, user_id: int, payload: dict) -> None:  # noqa: D401
        """Send *payload* to all sockets of *user_id*."""
        conns = self._connections.get(user_id, [])
        if not conns:
            return
        disconnected: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception as exc:  # pragma: no cover – log and drop
                logger.warning("Notify send failed: %s", exc)
                disconnected.append(ws)
        for ws in disconnected:
            await self.disconnect(ws, user_id)


# Singleton
notify_manager = NotifyManager()
