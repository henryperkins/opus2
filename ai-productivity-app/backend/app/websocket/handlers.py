from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Union
import logging

from app.models.user import User
from app.models.chat import ChatMessage
from app.services.chat_service import ChatService
from app.services.knowledge_service import KnowledgeService
from app.services.vector_service import vector_service
from app.embeddings.generator import EmbeddingGenerator
from app.chat.processor import ChatProcessor
from .manager import connection_manager

logger = logging.getLogger(__name__)


async def handle_chat_connection(
    websocket: WebSocket,
    session_id: int,
    current_user: User,
    db: Union[Session, AsyncSession],
):
    """Handle WebSocket connection for chat session."""
    await connection_manager.connect(websocket, session_id, current_user.id)
    logger.debug(f"User {current_user.id} connected to session {session_id}")
    chat_service = ChatService(db)

    # Initialize knowledge service for RAG capabilities
    knowledge_service = None
    try:
        await vector_service.initialize()
        embedding_generator = EmbeddingGenerator()
        knowledge_service = KnowledgeService(vector_service, embedding_generator)
        logger.info("Knowledge service initialized for chat processor")
    except Exception as e:
        logger.warning(f"Failed to initialize knowledge service: {e}")

    chat_processor = ChatProcessor(db, kb=knowledge_service)

    try:
        # Send connection confirmation
        await websocket.send_json(
            {"type": "connected", "user_id": current_user.id, "session_id": session_id}
        )
        logger.debug("Sent connection confirmation")

        # Send recent messages
        recent_messages = await chat_service.get_session_messages(session_id, limit=20)
        await websocket.send_json(
            {
                "type": "message_history",
                "messages": [serialize_message(m) for m in recent_messages],
            }
        )
        logger.debug(
            "Sent %d recent messages to user %s",
            len(recent_messages),
            current_user.id,
        )

        # Message handling loop
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received data: {data}")

            if data["type"] == "message":
                # Process user message
                user_message = await chat_service.create_message(
                    session_id=session_id,
                    content=data["content"],
                    role="user",
                    user_id=current_user.id,
                    metadata=data.get("metadata"),
                )

                # Process with AI
                await chat_processor.process_message(
                    session_id=session_id, message=user_message, websocket=websocket
                )

            elif data["type"] == "edit_message":
                await chat_service.update_message(
                    message_id=data["message_id"],
                    content=data["content"],
                    user_id=current_user.id,
                )

            elif data["type"] == "delete_message":
                await chat_service.delete_message(
                    message_id=data["message_id"], user_id=current_user.id
                )

            elif data["type"] == "typing":
                # Broadcast typing indicator
                await connection_manager.send_message(
                    {
                        "type": "typing",
                        "user_id": current_user.id,
                        # Accept both new ``is_typing`` and legacy ``typing`` keys
                        "typing": data.get("is_typing", data.get("typing", False)),
                    },
                    session_id,
                )

            elif data["type"] == "request_config":
                # Send current configuration to requesting client
                try:
                    from app.services.unified_config_service import UnifiedConfigService
                    from app.database import SessionLocal

                    with SessionLocal() as db:
                        unified_service = UnifiedConfigService(db)
                        current_config = unified_service.get_current_config()
                        # Convert to legacy format for WebSocket compatibility
                        config_dict = current_config.to_runtime_config()

                    await websocket.send_json(
                        {
                            "type": "config_update",
                            "config": config_dict,
                            "requested": True,
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to send config to client: {e}")
                    await websocket.send_json(
                        {"type": "error", "message": "Failed to retrieve configuration"}
                    )

    except WebSocketDisconnect:
        logger.info(f"User {current_user.id} disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"type": "error", "message": "Internal server error"})
    finally:
        await connection_manager.disconnect(websocket, session_id, current_user.id)


def serialize_message(message: ChatMessage) -> dict:
    """Convert message to JSON-serializable format."""
    try:
        return {
            "id": message.id,
            "content": message.content,
            "role": message.role,
            "user_id": message.user_id,
            "created_at": message.created_at.isoformat(),
            "is_edited": message.is_edited,
            "edited_at": message.edited_at.isoformat() if message.edited_at else None,
            "code_snippets": message.code_snippets or [],
            "referenced_files": message.referenced_files or [],
            "referenced_chunks": message.referenced_chunks or [],
            "applied_commands": message.applied_commands or {},
            # Include RAG metadata to match REST API format
            "metadata": {
                "ragUsed": message.rag_used,
                "ragConfidence": (
                    float(message.rag_confidence) if message.rag_confidence else None
                ),
                "knowledgeSourcesCount": message.knowledge_sources_count,
                "searchQuery": message.search_query_used,
                "contextTokensUsed": message.context_tokens_used,
                "ragStatus": message.rag_status,
                "ragError": message.rag_error_message,
            },
        }
    except Exception as e:
        logger.error(f"Failed to serialize message {message.id}: {e}")
        # Return a fallback message to prevent WebSocket connection failure
        return {
            "id": message.id,
            "content": message.content,
            "role": message.role,
            "user_id": message.user_id,
            "created_at": message.created_at.isoformat() if message.created_at else "",
            "is_edited": False,
            "edited_at": None,
            "code_snippets": [],
            "referenced_files": [],
            "referenced_chunks": [],
            "applied_commands": {},
            "metadata": {
                "ragUsed": False,
                "ragConfidence": None,
                "knowledgeSourcesCount": 0,
                "searchQuery": None,
                "contextTokensUsed": 0,
                "ragStatus": "error",
                "ragError": "Serialization failed",
            },
        }
