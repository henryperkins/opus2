from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Dict
import json
from datetime import datetime

from app.models.chat import ChatSession, ChatMessage
from app.models.timeline import TimelineEvent
from app.schemas.chat import MessageCreate, MessageUpdate
from app.websocket.manager import connection_manager


class ChatService:
    """Business logic for chat operations."""

    def __init__(self, db: Session):
        self.db = db

    async def create_session(
        self, project_id: int, title: Optional[str] = None
    ) -> ChatSession:
        """Create new chat session."""
        session = ChatSession(
            project_id=project_id,
            title=title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )
        self.db.add(session)
        self.db.commit()

        # Add timeline event
        event = TimelineEvent(
            project_id=project_id,
            event_type="chat_created",
            title=f"Started chat: {session.title}",
            event_metadata={"session_id": session.id},
        )
        self.db.add(event)
        self.db.commit()

        return session

    async def create_message(
        self,
        session_id: int,
        content: str,
        role: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> ChatMessage:
        """Create and broadcast new message."""
        message = ChatMessage(
            session_id=session_id,
            content=content,
            role=role,
            user_id=user_id,
            code_snippets=metadata.get("code_snippets", []) if metadata else [],
            referenced_files=metadata.get("referenced_files", []) if metadata else [],
            applied_commands=metadata.get("commands", {}) if metadata else {},
        )
        self.db.add(message)
        self.db.commit()

        # Update session timestamp
        session = self.db.query(ChatSession).filter_by(id=session_id).first()
        session.updated_at = datetime.utcnow()
        self.db.commit()

        # Broadcast to connected clients
        await self._broadcast_message(message)

        return message

    async def update_message(
        self, message_id: int, content: str, user_id: int
    ) -> Optional[ChatMessage]:
        """Edit existing message."""
        message = (
            self.db.query(ChatMessage)
            .filter_by(id=message_id, user_id=user_id, is_deleted=False)
            .first()
        )

        if not message:
            return None

        # Store original content
        if not message.is_edited:
            message.original_content = message.content

        message.content = content
        message.is_edited = True
        message.edited_at = datetime.utcnow()

        self.db.commit()

        # Broadcast update
        await self._broadcast_message_update(message)

        return message

    async def delete_message(self, message_id: int, user_id: int) -> bool:
        """Soft delete message."""
        message = (
            self.db.query(ChatMessage).filter_by(id=message_id, user_id=user_id).first()
        )

        if not message:
            return False

        message.is_deleted = True
        self.db.commit()

        # Broadcast deletion
        await connection_manager.send_message(
            {"type": "message_deleted", "message_id": message_id}, message.session_id
        )

        return True

    def get_session_messages(
        self, session_id: int, limit: int = 50, before_id: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get messages with pagination."""
        query = self.db.query(ChatMessage).filter_by(
            session_id=session_id, is_deleted=False
        )

        if before_id:
            query = query.filter(ChatMessage.id < before_id)

        return query.order_by(ChatMessage.id.desc()).limit(limit).all()

    async def _broadcast_message(self, message: ChatMessage):
        """Broadcast new message to session."""
        await connection_manager.send_message(
            {
                "type": "new_message",
                "message": {
                    "id": message.id,
                    "content": message.content,
                    "role": message.role,
                    "user_id": message.user_id,
                    "created_at": message.created_at.isoformat(),
                    "code_snippets": message.code_snippets,
                    "referenced_files": message.referenced_files,
                },
            },
            message.session_id,
        )

    async def _broadcast_message_update(self, message: ChatMessage):
        """Broadcast message edit."""
        await connection_manager.send_message(
            {
                "type": "message_updated",
                "message": {
                    "id": message.id,
                    "content": message.content,
                    "edited_at": message.edited_at.isoformat(),
                },
            },
            message.session_id,
        )
