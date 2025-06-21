"""Chat API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional

from app.dependencies import DatabaseDep, CurrentUserRequired
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse,
    ChatSessionListResponse, MessageResponse
)
from app.services.chat_service import ChatService
from app.websocket.handlers import handle_chat_connection
from app.auth.utils import get_current_user_ws
from app.chat.commands import command_registry

# ---------------------------------------------------------------------------
# Module level logger
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    project_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List chat sessions with optional filtering."""
    logger.info(
        "Listing chat sessions – user_id=%s project_id=%s is_active=%s limit=%s offset=%s",
        current_user.id,
        project_id,
        is_active,
        limit,
        offset,
    )

    query = db.query(ChatSession)

    if project_id:
        query = query.filter(ChatSession.project_id == project_id)
    if is_active is not None:
        query = query.filter(ChatSession.is_active == is_active)

    total = query.count()
    sessions = query.offset(offset).limit(limit).all()

    # Add message count
    items = []
    for session in sessions:
        response = ChatSessionResponse.from_orm(session)
        response.message_count = db.query(ChatMessage).filter_by(
            session_id=session.id, is_deleted=False
        ).count()
        items.append(response)

    return ChatSessionListResponse(items=items, total=total)


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    session_data: ChatSessionCreate,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Create a new chat session."""
    logger.info(
        "Create chat session – user_id=%s project_id=%s title=%s",
        current_user.id,
        session_data.project_id,
        session_data.title,
    )

    service = ChatService(db)
    session = await service.create_session(
        project_id=session_data.project_id,
        title=session_data.title
    )

    logger.debug("Session created with id=%s", session.id)

    return ChatSessionResponse.from_orm(session)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Get chat session details."""
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response = ChatSessionResponse.from_orm(session)
    response.message_count = db.query(ChatMessage).filter_by(
        session_id=session.id, is_deleted=False
    ).count()

    return response


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: int,
    update_data: ChatSessionUpdate,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Update chat session."""
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if update_data.title is not None:
        session.title = update_data.title
    if update_data.is_active is not None:
        session.is_active = update_data.is_active

    db.commit()
    return ChatSessionResponse.from_orm(session)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Delete a chat session."""
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = None
):
    """Get messages for a chat session."""
    service = ChatService(db)
    messages = service.get_session_messages(session_id, limit, before_id)
    return [MessageResponse.from_orm(msg) for msg in messages]


@router.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: int,
    db: DatabaseDep
):
    """WebSocket endpoint for real-time chat."""
    # Authenticate WebSocket connection
    try:
        # ------------------------------------------------------------------
        # Authentication for WebSocket connection
        # ------------------------------------------------------------------
        # Prefer cookie-based auth (the browser automatically includes the
        # HttpOnly *access_token* cookie during the WebSocket handshake).
        # Fallback to the explicit "token" query-parameter for backwards
        # compatibility and automated tests which conveniently inject it.
        # ------------------------------------------------------------------

        token: str | None = None

        # 1. Attempt to read Bearer token from cookies (preferred)
        token = websocket.cookies.get("access_token")  # type: ignore[attr-defined]

        # 2. Fallback to ?token= query parameter
        if not token:
            token = websocket.query_params.get("token")

        if not token:
            await websocket.close(code=1008, reason="Missing token")
            return

        current_user = await get_current_user_ws(websocket, token, db)
        if not current_user:
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Handle chat connection
        await handle_chat_connection(websocket, session_id, current_user, db)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))


# ---------------------------------------------------------------------------
# Autocomplete – slash-command suggestions
# ---------------------------------------------------------------------------


@router.get("/suggestions")
async def get_command_suggestions(q: str = Query("", min_length=0, max_length=100)) -> List[dict]:  # noqa: D401
    """Return slash-command autocompletion suggestions.

    The *frontend* sends the user’s **partial input** via the ``q`` query
    parameter as soon as the first ``/`` is typed.  This handler simply
    delegates to :pyfunc:`app.chat.commands.CommandRegistry.get_suggestions`.
    """

    # Quick early-out to avoid unnecessary work for empty queries.
    if not q:
        return []

    return command_registry.get_suggestions(q)
