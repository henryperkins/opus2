"""WebSocket endpoint for user-level notifications."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status

from app.dependencies import CurrentUserRequired
from app.websocket.notify_manager import notify_manager

router = APIRouter(prefix="/ws", tags=["notifications"], include_in_schema=False)


@router.websocket("/notify")
async def websocket_notify(
    websocket: WebSocket,
    current_user: CurrentUserRequired,
):  # noqa: D401
    """Push server-side events to the authenticated user."""
    await notify_manager.connect(websocket, current_user.id)
    try:
        while True:
            # Notifications are *server-push* only.  We still need to read
            # incoming messages to detect client pings or the connection will
            # close after ~30 s under some browsers.  For MVP we simply discard.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await notify_manager.disconnect(websocket, current_user.id)
