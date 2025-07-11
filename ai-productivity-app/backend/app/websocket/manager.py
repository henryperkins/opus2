# flake8: max-line-length = 120
# pylint: disable=line-too-long, unused-import
from typing import Dict, List, Set
from fastapi import WebSocket
import asyncio
import logging

logger = logging.getLogger(__name__)

# Maximum concurrent WebSocket connections allowed per authenticated user.
# Protects against resource-exhaustion attacks while permitting legitimate
# multi-tab usage. This guard complements rate-limiting at the HTTP layer.
MAX_CONNECTIONS_PER_USER = 20


class ConnectionManager:
    """Manage WebSocket connections for chat sessions."""

    def __init__(self):
        # session_id -> list of websockets
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # user_id -> set of session_ids
        self.user_sessions: Dict[int, Set[int]] = {}
        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, session_id: int, user_id: int):
        """Accept new connection.

        Adds a per-user connection limit to mitigate denial-of-service
        scenarios where a malicious client opens thousands of sockets.
        """
        await websocket.accept()

        async with self._lock:
            # ------------------------------------------------------------------
            # Enforce per-user connection cap
            # ------------------------------------------------------------------
            user_sessions = self.user_sessions.get(user_id, set())
            existing_connections = sum(
                len(self.active_connections.get(sid, [])) for sid in user_sessions
            )
            if existing_connections >= MAX_CONNECTIONS_PER_USER:
                # Politely refuse – use app-specific close code (4000) so the
                # frontend can handle it distinctly if needed.
                await websocket.close(code=4000, reason="Connection limit exceeded")
                logger.warning(
                    "Rejected WebSocket %s for user %s – connection limit exceeded (%s)",
                    id(websocket),
                    user_id,
                    existing_connections,
                )
                return

            if session_id not in self.active_connections:
                self.active_connections[session_id] = []
            self.active_connections[session_id].append(websocket)
            logger.debug(
                "Accepted WebSocket %s for user %s in session %s",
                id(websocket),
                user_id,
                session_id,
            )

            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)

        logger.info(f"User {user_id} connected to session {session_id}")

    async def disconnect(self, websocket: WebSocket, session_id: int, user_id: int):
        """Remove connection."""
        async with self._lock:
            if session_id in self.active_connections:
                try:
                    self.active_connections[session_id].remove(websocket)
                except ValueError:
                    # Socket was already removed elsewhere – benign race
                    logger.debug(
                        "WebSocket %s already absent from session %s on disconnect",
                        id(websocket),
                        session_id,
                    )
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
            logger.debug(
                "Disconnected WebSocket %s for user %s from session %s",
                id(websocket),
                user_id,
                session_id,
            )

            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]

    async def send_message(self, message: dict, session_id: int):
        """Send message to all connections in a session."""
        logger.debug("Broadcasting message to session %s: %s", session_id, message)

        async with self._lock:
            if session_id not in self.active_connections:
                return

            # Create a copy to iterate over to avoid race conditions
            connections = list(self.active_connections[session_id])

        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(
                    "Failed to send message to WebSocket %s: %s", id(websocket), e
                )
                disconnected.append(websocket)

        # Clean up disconnected sockets
        if disconnected:
            async with self._lock:
                if session_id in self.active_connections:
                    for ws in disconnected:
                        try:
                            self.active_connections[session_id].remove(ws)
                        except ValueError:
                            # Socket already removed by another thread
                            pass

                    # Remove empty session
                    if not self.active_connections[session_id]:
                        del self.active_connections[session_id]

    async def broadcast_to_user(self, message: dict, user_id: int):
        """Send message to all sessions for a user."""
        logger.debug(
            "Broadcasting message to user %s across all sessions: %s", user_id, message
        )

        async with self._lock:
            if user_id not in self.user_sessions:
                return
            session_ids = list(self.user_sessions[user_id])

        for session_id in session_ids:
            await self.send_message(message, session_id)

    def get_session_users(self, session_id: int) -> int:
        """Get count of users in session."""
        return len(self.active_connections.get(session_id, []))

    async def broadcast_config_update(self, config_data: dict):
        """Broadcast configuration updates.

        This now:
        1. Sends to every **chat-level** connection (session-scoped).
        2. Relays the same payload via ``notify_manager`` so that clients
           connected through the global notifications channel also receive
           instant updates.
        """
        message = {
            "type": "config_update",
            "config": config_data,
            "timestamp": asyncio.get_event_loop().time(),
        }

        logger.info("Broadcasting config update to chat sessions and notify channel")

        # 1) Chat-session broadcast
        async with self._lock:
            session_ids = list(self.active_connections.keys())

        for session_id in session_ids:
            await self.send_message(message, session_id)

        # 2) Global user-level broadcast (notification sockets)
        try:
            # Local import to avoid potential circular dependency
            from app.websocket.notify_manager import (
                notify_manager,
            )  # pylint: disable=import-error

            # Fire-and-forget; failures are logged but do not break the caller
            await notify_manager.broadcast(message)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to relay config update via notify_manager: %s", exc)


# Global instance
connection_manager = ConnectionManager()
