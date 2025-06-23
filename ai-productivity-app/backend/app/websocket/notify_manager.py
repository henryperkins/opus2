"""Enhanced WebSocket notification manager with task cleanup."""
import asyncio
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
from datetime import datetime

from fastapi import WebSocket
import logging

from app.config import settings
from app.middleware.correlation_id import get_request_id

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages background tasks with proper cleanup."""

    def __init__(self):
        self._tasks: Dict[int, Set[asyncio.Task]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def spawn(self, user_id: int, coro) -> asyncio.Task:
        """Spawn a task and track it for cleanup."""
        task = asyncio.create_task(coro)

        async with self._lock:
            self._tasks[user_id].add(task)

        # Add cleanup callback
        def cleanup_callback(t):
            asyncio.create_task(self._remove_task(user_id, t))

        task.add_done_callback(cleanup_callback)
        return task

    async def _remove_task(self, user_id: int, task: asyncio.Task):
        """Remove completed task from tracking."""
        async with self._lock:
            if user_id in self._tasks:
                self._tasks[user_id].discard(task)
                if not self._tasks[user_id]:
                    del self._tasks[user_id]

    async def cancel_user_tasks(self, user_id: int) -> int:
        """Cancel all tasks for a user."""
        async with self._lock:
            tasks = list(self._tasks.get(user_id, set()))

        if not tasks:
            return 0

        # Cancel all tasks
        for task in tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellation with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Timeout waiting for %s tasks to cancel for user %s",
                len(tasks),
                user_id,
            )

        # Clean up tracking
        async with self._lock:
            if user_id in self._tasks:
                del self._tasks[user_id]

        return len(tasks)

    async def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        async with self._lock:
            total_tasks = sum(len(tasks) for tasks in self._tasks.values())
            active_users = len(self._tasks)

            # Get per-user stats
            user_stats = {}
            for user_id, tasks in self._tasks.items():
                active = sum(1 for t in tasks if not t.done())
                user_stats[user_id] = {
                    "total": len(tasks),
                    "active": active,
                    "completed": len(tasks) - active
                }

        return {
            "total_tasks": total_tasks,
            "active_users": active_users,
            "user_stats": user_stats
        }


class EnhancedNotifyManager:
    """WebSocket manager with task tracking and cleanup."""

    def __init__(self):
        self.connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        self.task_manager = TaskManager()
        self._connection_lock = asyncio.Lock()

        # Track WebSocket task control
        self.task_tracking_enabled = getattr(
            settings, "ws_task_tracking", True
        )

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept WebSocket connection."""
        await websocket.accept()
        async with self._connection_lock:
            self.connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected via WebSocket")

    async def disconnect(self, websocket: WebSocket, user_id: int):
        """Handle WebSocket disconnection with cleanup."""
        async with self._connection_lock:
            if user_id in self.connections:
                self.connections[user_id].discard(websocket)
                if not self.connections[user_id]:
                    del self.connections[user_id]

        # Cancel all tasks for this user if no more connections
        if user_id not in self.connections and self.task_tracking_enabled:
            cancelled = await self.task_manager.cancel_user_tasks(user_id)
            if cancelled > 0:
                logger.info(
                    "Cancelled %s tasks for disconnected user %s",
                    cancelled,
                    user_id,
                )

        logger.info(f"User {user_id} disconnected from WebSocket")

    async def send(self, user_id: int, message: dict) -> None:
        """Send message to user with request ID."""
        # Add request ID to all WebSocket messages
        request_id = get_request_id()
        if request_id:
            message["request_id"] = request_id

        if user_id not in self.connections:
            return

        # Get current connections snapshot
        async with self._connection_lock:
            websockets = list(self.connections.get(user_id, set()))

        # Send to all connections for this user
        failed_connections = []
        for websocket in websockets:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                failed_connections.append(websocket)

        # Clean up failed connections
        for ws in failed_connections:
            await self.disconnect(ws, user_id)

    async def send_async(self, user_id: int, message: dict) -> None:
        """Send message asynchronously with task tracking."""
        if self.task_tracking_enabled:
            await self.task_manager.spawn(
                user_id,
                self.send(user_id, message)
            )
        else:
            # Fallback to simple fire-and-forget
            asyncio.create_task(self.send(user_id, message))

    async def broadcast(
        self, message: dict, user_ids: Optional[List[int]] = None
    ):
        """Broadcast message to multiple users."""
        if user_ids is None:
            async with self._connection_lock:
                user_ids = list(self.connections.keys())

        # Send concurrently to all users
        tasks = []
        for user_id in user_ids:
            if self.task_tracking_enabled:
                task = await self.task_manager.spawn(
                    user_id,
                    self.send(user_id, message)
                )
                tasks.append(task)
            else:
                tasks.append(asyncio.create_task(self.send(user_id, message)))

        # Wait for all sends to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection and task statistics."""
        async with self._connection_lock:
            connection_stats = {
                "total_users": len(self.connections),
                "total_connections": sum(
                    len(conns) for conns in self.connections.values()
                ),
                "users": {
                    user_id: len(conns)
                    for user_id, conns in self.connections.items()
                },
            }

        if self.task_tracking_enabled:
            task_stats = await self.task_manager.get_stats()
        else:
            task_stats = {}

        return {
            "connections": connection_stats,
            "tasks": task_stats,
            "task_tracking_enabled": self.task_tracking_enabled
        }


# Global instance
notify_manager = EnhancedNotifyManager()


# Example usage in import job with proper cleanup
async def _notify_with_cleanup(user_id: int, message: dict):
    """Send notification with automatic cleanup."""
    try:
        await notify_manager.send_async(user_id, message)
    except Exception as e:
        logger.error(f"Notification failed for user {user_id}: {e}")


# Background worker heartbeat for health checks
async def worker_heartbeat(worker_id: str, redis_client):
    """Update worker heartbeat in Redis."""
    while True:
        try:
            key = f"worker:{worker_id}"
            await redis_client.set(key, datetime.utcnow().isoformat(), ex=60)
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Worker heartbeat failed: {e}")
            await asyncio.sleep(5)
