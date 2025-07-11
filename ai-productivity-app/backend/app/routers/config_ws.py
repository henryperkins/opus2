"""WebSocket endpoint for AI-configuration updates.

The frontend connects to ``/ws/config`` to receive real-time configuration
events (``config_update``, ``config_batch_update``, conflict notifications …).

Internally we reuse the *notify_manager* that is already responsible for
user-scoped server-push notifications.  ``connection_manager`` (chat scope)
would technically work as well but would unnecessarily tie the global
configuration channel to an arbitrary *session_id* value.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# ----------------------------------------------------------------------------
# Local imports – delayed to avoid circular dependencies.
# ----------------------------------------------------------------------------

from app.dependencies import CurrentUserRequired  # noqa: E402 – after FastAPI
from app.websocket.notify_manager import notify_manager  # noqa: E402


# ``include_in_schema=False`` hides the endpoint from the public OpenAPI docs
# because it is consumed exclusively by the internal React app.
router = APIRouter(prefix="/ws", tags=["ai-configuration"], include_in_schema=False)


@router.websocket("/config")
async def websocket_config_updates(
    websocket: WebSocket,
    current_user: CurrentUserRequired,
):  # noqa: D401 – FastAPI websocket signature
    """Push real-time AI-configuration events to the authenticated user."""

    # The *notify_manager* applies the same per-user connection cap used by
    # chat sessions which protects the server against resource exhaustion
    # attacks while allowing legitimate multi-tab usage.
    await notify_manager.connect(websocket, current_user.id)

    try:
        # The server currently implements *server-push* only.  Still, we must
        # read incoming frames (e.g. ping/pong or future client messages)
        # otherwise the browser might close the socket after a timeout.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Normal closure initiated by the client – nothing to log.
        pass
    finally:
        await notify_manager.disconnect(websocket, current_user.id)
