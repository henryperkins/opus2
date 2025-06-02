from typing import Dict, List, Set
from fastapi import WebSocket
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


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
        """Accept new connection."""
        await websocket.accept()

        async with self._lock:
            if session_id not in self.active_connections:
                self.active_connections[session_id] = []
            self.active_connections[session_id].append(websocket)

            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)

        logger.info(f"User {user_id} connected to session {session_id}")

    async def disconnect(self, websocket: WebSocket, session_id: int, user_id: int):
        """Remove connection."""
        async with self._lock:
            if session_id in self.active_connections:
                self.active_connections[session_id].remove(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]

            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]

    async def send_message(self, message: dict, session_id: int):
        """Send message to all connections in a session."""
        if session_id in self.active_connections:
            disconnected = []

            for websocket in self.active_connections[session_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message: {e}")
                    disconnected.append(websocket)

            # Clean up disconnected sockets
            for ws in disconnected:
                self.active_connections[session_id].remove(ws)

    async def broadcast_to_user(self, message: dict, user_id: int):
        """Send message to all sessions for a user."""
        if user_id in self.user_sessions:
            for session_id in self.user_sessions[user_id]:
                await self.send_message(message, session_id)

    def get_session_users(self, session_id: int) -> int:
        """Get count of users in session."""
        return len(self.active_connections.get(session_id, []))


# Global instance
connection_manager = ConnectionManager()
