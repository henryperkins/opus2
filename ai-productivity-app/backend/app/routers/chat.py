"""Chat API endpoints."""
import logging
from typing import List, Optional

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)

from app.dependencies import CurrentUserRequired, DatabaseDep
from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
    MessageCreate,
    MessageUpdate,
    MessageResponse,
)
from app.services.chat_service import ChatService
from app.websocket.handlers import handle_chat_connection
from app.auth.utils import get_current_user_ws
from app.chat.commands import command_registry
from app.chat.processor import ChatProcessor

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
    offset: int = Query(0, ge=0),
):
    """List chat sessions with optional filtering."""
    logger.info(
        "Listing chat sessions – user_id=%s project_id=%s is_active=%s "
        "limit=%s offset=%s",
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
    items: List[ChatSessionResponse] = []
    for session in sessions:
        response = ChatSessionResponse.from_orm(session)
        response.message_count = (
            db.query(ChatMessage)
            .filter_by(session_id=session.id, is_deleted=False)
            .count()
        )
        items.append(response)

    return ChatSessionListResponse(items=items, total=total)


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    session_data: ChatSessionCreate,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
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
        project_id=session_data.project_id, title=session_data.title
    )

    logger.debug("Session created with id=%s", session.id)

    return ChatSessionResponse.from_orm(session)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: int,
    _current_user: CurrentUserRequired,  # unused – keep for auth dependency
    db: DatabaseDep,
):
    """Get chat session details."""
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response = ChatSessionResponse.from_orm(session)
    response.message_count = (
        db.query(ChatMessage)
        .filter_by(session_id=session.id, is_deleted=False)
        .count()
    )

    return response


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: int,
    update_data: ChatSessionUpdate,
    _current_user: CurrentUserRequired,  # unused – keep for auth dependency
    db: DatabaseDep,
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
    _current_user: CurrentUserRequired,  # unused – keep for auth dependency
    db: DatabaseDep,
):
    """Delete a chat session."""
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()


@router.get(
    "/sessions/{session_id}/messages",
)
async def get_messages(
    session_id: int,
    _current_user: CurrentUserRequired,  # unused – keep for auth dependency
    db: DatabaseDep,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = None,
):
    """Get messages for a chat session."""
    service = ChatService(db)
    messages = await service.get_session_messages(session_id, limit, before_id)

    # Transform messages to include metadata in the format expected by frontend
    response_messages = []
    for msg in messages:
        msg_dict = MessageResponse.from_orm(msg).dict()

        # Add metadata object with RAG information to match WebSocket format
        msg_dict['metadata'] = {
            'ragUsed': msg.rag_used,
            'ragConfidence': float(msg.rag_confidence) if msg.rag_confidence else None,
            'knowledgeSourcesCount': msg.knowledge_sources_count,
            'searchQuery': msg.search_query_used,
            'contextTokensUsed': msg.context_tokens_used,
            'ragStatus': msg.rag_status,
            'ragError': msg.rag_error_message,
        }
        response_messages.append(msg_dict)

    return response_messages


# ---------------------------------------------------------------------------
# Message CRUD endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def create_message(
    session_id: int,
    message: MessageCreate,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Create a new message in a chat session."""
    service = ChatService(db)

    # Log incoming user message for debugging
    logger.info("=== NEW USER MESSAGE ===")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"User ID: {current_user.id}")
    logger.info(f"Role: {message.role}")
    logger.info(f"Content: {message.content}")
    logger.info(f"Code Snippets: {len(message.code_snippets)}")
    logger.info(f"Referenced Files: {message.referenced_files}")
    logger.info(f"Referenced Chunks: {message.referenced_chunks}")
    logger.info(f"Applied Commands: {message.applied_commands}")

    # Extract metadata from the schema fields
    metadata = {
        'code_snippets': message.code_snippets,
        'referenced_files': message.referenced_files,
        'referenced_chunks': message.referenced_chunks,
        'applied_commands': message.applied_commands,
    }

    msg = await service.create_message(
        session_id=session_id,
        content=message.content,
        # Handle raw Enum instance *or* pre-coerced string safely
        role=message.role.value if hasattr(message.role, "value") else message.role,
        user_id=current_user.id,
        metadata=metadata,
    )

    # Trigger AI processing for user messages
    if msg.role == 'user':
        import asyncio
        from app.websocket.mock import MockWebSocket

        # Create a mock WebSocket for the REST API context
        mock_websocket = MockWebSocket()

        # Process with AI in background - create async session
        from app.database import AsyncSessionLocal

        async def process_with_async_session():
            async with AsyncSessionLocal() as async_db:
                # Initialize knowledge service for RAG capabilities
                knowledge_service = None
                try:
                    from app.services.vector_service import vector_service
                    from app.embeddings.generator import EmbeddingGenerator
                    from app.services.knowledge_service import KnowledgeService

                    await vector_service.initialize()
                    embedding_generator = EmbeddingGenerator()
                    knowledge_service = KnowledgeService(vector_service, embedding_generator)
                    logger.info("Knowledge service initialized for REST API chat processor")
                except Exception as e:
                    logger.warning(f"Failed to initialize knowledge service for REST API: {e}")

                processor = ChatProcessor(async_db, kb=knowledge_service)
                await processor.process_message(
                    session_id=session_id,
                    message=msg,
                    websocket=mock_websocket
                )

        asyncio.create_task(process_with_async_session())

    return MessageResponse.from_orm(msg)


@router.patch(
    "/messages/{message_id}",
    response_model=MessageResponse,
)
async def update_message(
    message_id: int,
    update: MessageUpdate,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Update an existing chat message."""
    service = ChatService(db)
    msg = await service.update_message(
        message_id=message_id, content=update.content, user_id=current_user.id
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return MessageResponse.from_orm(msg)


@router.delete("/messages/{message_id}", status_code=204)
async def delete_message(
    message_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Soft-delete a chat message.

    Behaviour:
    • Returns **404** when the message does not exist.
    • Returns **403** when the authenticated user is *not* the author.
    • Returns **204** (empty) on successful soft-delete.
    """
    # ‑- verify existence
    message = db.query(ChatMessage).filter_by(id=message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # ------------------------------------------------------------------
    # Authorisation rules
    # ------------------------------------------------------------------
    # 1. The *author* of the message may always delete their own content.
    # 2. Users flagged as *admin* may delete **any** message.
    # Any other request is rejected with HTTP 403.

# ------------------------------------------------------------------
#  Additional rule – allow the *owner* of the **project** to delete any
#  message within their project’s chat sessions.  This resolves the scenario
#  where a user attempts to remove an *assistant* message which naturally has
#  no *author* (``user_id is NULL``) and therefore failed the original
#  author-only check.
# ------------------------------------------------------------------

    is_author = message.user_id == current_user.id
    is_admin = getattr(current_user, "is_admin", False)

    # Lazily loaded relationship works for both sync and async sessions here
    try:
        project_owner_id = message.session.project.owner_id  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover – relationship not resolvable
        project_owner_id = None

    is_project_owner = project_owner_id == current_user.id

    if not (is_author or is_admin or is_project_owner):
        raise HTTPException(
            status_code=403, detail="Not authorised to delete this message"
        )

    # perform soft-delete
    service = ChatService(db)
    await service.delete_message(message_id, current_user.id)


@router.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: int,
    db: DatabaseDep,
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

        token = websocket.cookies.get("access_token") or websocket.query_params.get(
            "token"
        )

        if not token:
            logger.warning(
                "WebSocket connection rejected: Missing authentication token"
            )
            await websocket.close(code=1008, reason="Missing token")
            return

        current_user = await get_current_user_ws(websocket, token, db)
        if not current_user:
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Create async session for chat processing since ChatProcessor expects async
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as async_db:
            await handle_chat_connection(websocket, session_id, current_user, async_db)

    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: W0718 – keep broad to ensure WS closes
        await websocket.close(code=1011, reason=str(exc))


# ---------------------------------------------------------------------------
# Autocomplete – slash-command suggestions
# ---------------------------------------------------------------------------


@router.get("/suggestions")
async def get_command_suggestions(
    q: str = Query("", min_length=0, max_length=100),
) -> List[dict]:  # noqa: D401
    """Return slash-command autocompletion suggestions.

    The *frontend* sends the user’s **partial input** via the ``q`` query
    parameter as soon as the first ``/`` is typed.  This handler simply
    delegates to :pyfunc:`app.chat.commands.CommandRegistry.get_suggestions`.
    """
    # Quick early-out to avoid unnecessary work for empty queries.
    if not q:
        return []

    return command_registry.get_suggestions(q)
