from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import logging

from app.models.user import User
from app.models.chat import ChatMessage
from app.services.chat_service import ChatService
from app.chat.processor import ChatProcessor
from .manager import connection_manager

logger = logging.getLogger(__name__)


async def handle_chat_connection(
    websocket: WebSocket,
    session_id: int,
    current_user: User,
    db: Session
):
    """Handle WebSocket connection for chat session."""
    await connection_manager.connect(websocket, session_id, current_user.id)
    logger.debug(f"User {current_user.id} connected to session {session_id}")
    chat_service = ChatService(db)
    chat_processor = ChatProcessor(db)

    try:
        # Send connection confirmation
        await websocket.send_json({
            'type': 'connected',
            'user_id': current_user.id,
            'session_id': session_id
        })
        logger.debug("Sent connection confirmation")

        # Send recent messages
        recent_messages = chat_service.get_session_messages(
            session_id, limit=20
        )
        await websocket.send_json({
            'type': 'message_history',
            'messages': [serialize_message(m) for m in reversed(recent_messages)],
        })
        logger.debug(
            "Sent %d recent messages to user %s",
            len(recent_messages),
            current_user.id,
        )

        # Message handling loop
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received data: {data}")

            if data['type'] == 'message':
                # Process user message
                user_message = await chat_service.create_message(
                    session_id=session_id,
                    content=data['content'],
                    role='user',
                    user_id=current_user.id,
                    metadata=data.get('metadata')
                )

                # Process with AI
                await chat_processor.process_message(
                    session_id=session_id,
                    message=user_message,
                    websocket=websocket
                )

            elif data['type'] == 'edit_message':
                await chat_service.update_message(
                    message_id=data['message_id'],
                    content=data['content'],
                    user_id=current_user.id
                )

            elif data['type'] == 'delete_message':
                await chat_service.delete_message(
                    message_id=data['message_id'],
                    user_id=current_user.id
                )

            elif data['type'] == 'typing':
                # Broadcast typing indicator
                await connection_manager.send_message({
                    'type': 'user_typing',
                    'user_id': current_user.id,
                    # Accept both new ``is_typing`` and legacy ``typing`` keys
                    'is_typing': data.get('is_typing', data.get('typing', False))
                }, session_id)
                
            elif data['type'] == 'request_config':
                # Send current configuration to requesting client
                try:
                    from app.services.config_service import ConfigService
                    config_service = ConfigService(db)
                    current_config = config_service.get_all_config()
                    
                    await websocket.send_json({
                        'type': 'config_update', 
                        'config': current_config,
                        'requested': True
                    })
                except Exception as e:
                    logger.error(f"Failed to send config to client: {e}")
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Failed to retrieve configuration'
                    })

    except WebSocketDisconnect:
        logger.info(f"User {current_user.id} disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            'type': 'error',
            'message': 'Internal server error'
        })
    finally:
        await connection_manager.disconnect(websocket, session_id, current_user.id)


def serialize_message(message: ChatMessage) -> dict:
    """Convert message to JSON-serializable format."""
    return {
        'id': message.id,
        'content': message.content,
        'role': message.role,
        'user_id': message.user_id,
        'created_at': message.created_at.isoformat(),
        'is_edited': message.is_edited,
        'edited_at': message.edited_at.isoformat() if message.edited_at else None,
        'code_snippets': message.code_snippets or [],
        'referenced_files': message.referenced_files or [],
        'referenced_chunks': message.referenced_chunks or [],
        'applied_commands': message.applied_commands or {}
    }
