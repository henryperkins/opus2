from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any, Union
import json
from datetime import datetime

from app.models.chat import ChatSession, ChatMessage
from app.models.timeline import TimelineEvent
from app.schemas.chat import MessageCreate, MessageUpdate
from app.websocket.manager import connection_manager


class ChatService:
    """Business logic for chat operations."""

    def __init__(self, db: Union[Session, AsyncSession]):
        self.db = db
        self.is_async = isinstance(db, AsyncSession)

    async def create_session(
        self, project_id: int, title: Optional[str] = None
    ) -> ChatSession:
        """Create new chat session."""
        session = ChatSession(
            project_id=project_id,
            title=title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            is_active=True,  # Explicitly set to avoid server_default/None mismatch
        )
        
        if self.is_async:
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            
            # Add timeline event
            event = TimelineEvent(
                project_id=project_id,
                event_type="chat_created",
                title=f"Started chat: {session.title}",
                event_metadata={"session_id": session.id},
            )
            self.db.add(event)
            await self.db.commit()
        else:
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
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
        rag_metadata: Optional[Dict] = None,
        broadcast: bool = True,
    ) -> ChatMessage:
        """Create and optionally broadcast new message."""
        message = ChatMessage(
            session_id=session_id,
            content=content,
            role=role,
            user_id=user_id,
            code_snippets=metadata.get("code_snippets", []) if metadata else [],
            referenced_files=metadata.get("referenced_files", []) if metadata else [],
            referenced_chunks=metadata.get("referenced_chunks", []) if metadata else [],
            applied_commands=metadata.get("applied_commands", {}) if metadata else {},
            # RAG tracking fields
            rag_used=rag_metadata.get("rag_used", False) if rag_metadata else False,
            rag_confidence=rag_metadata.get("rag_confidence") if rag_metadata else None,
            knowledge_sources_count=rag_metadata.get("knowledge_sources_count", 0) if rag_metadata else 0,
            search_query_used=rag_metadata.get("search_query_used") if rag_metadata else None,
            context_tokens_used=rag_metadata.get("context_tokens_used", 0) if rag_metadata else 0,
            rag_status=rag_metadata.get("rag_status") if rag_metadata else None,
            rag_error_message=rag_metadata.get("rag_error_message") if rag_metadata else None,
        )
        
        if self.is_async:
            self.db.add(message)
            await self.db.commit()
            
            # Update session timestamp
            session_result = await self.db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            session = session_result.scalar_one_or_none()
            if session:
                session.updated_at = datetime.utcnow()
                await self.db.commit()
        else:
            self.db.add(message)
            self.db.commit()
            
            # Update session timestamp
            session = self.db.query(ChatSession).filter_by(id=session_id).first()
            if session:
                session.updated_at = datetime.utcnow()
                self.db.commit()

        # Broadcast to connected clients if requested
        if broadcast:
            await self._broadcast_message(message)

        return message

    async def update_message(
        self, message_id: int, content: str, user_id: int
    ) -> Optional[ChatMessage]:
        """Edit existing message."""
        if self.is_async:
            result = await self.db.execute(
                select(ChatMessage).where(
                    ChatMessage.id == message_id,
                    ChatMessage.user_id == user_id,
                    ChatMessage.is_deleted == False
                )
            )
            message = result.scalar_one_or_none()
        else:
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

        if self.is_async:
            await self.db.commit()
        else:
            self.db.commit()

        # Broadcast update
        await self._broadcast_message_update(message)

        return message

    async def update_message_content(
        self, message_id: int, content: str, code_snippets: Optional[List[Dict[str, Any]]] = None,
        broadcast: bool = True
    ) -> Optional[ChatMessage]:
        """Update message content and code snippets (for AI messages)."""
        if self.is_async:
            result = await self.db.execute(
                select(ChatMessage).where(
                    ChatMessage.id == message_id,
                    ChatMessage.is_deleted == False
                )
            )
            message = result.scalar_one_or_none()
        else:
            message = (
                self.db.query(ChatMessage)
                .filter_by(id=message_id, is_deleted=False)
                .first()
            )

        if not message:
            return None

        message.content = content
        if code_snippets is not None:
            message.code_snippets = code_snippets

        if self.is_async:
            await self.db.commit()
        else:
            self.db.commit()

        # Broadcast update if requested
        if broadcast:
            await self._broadcast_message(message)

        return message

    async def delete_message(self, message_id: int, user_id: int) -> bool:
        """Soft delete message."""
        if self.is_async:
            result = await self.db.execute(
                select(ChatMessage).where(
                    ChatMessage.id == message_id,
                    ChatMessage.user_id == user_id
                )
            )
            message = result.scalar_one_or_none()
        else:
            message = (
                self.db.query(ChatMessage).filter_by(id=message_id, user_id=user_id).first()
            )

        if not message:
            return False

        message.is_deleted = True
        
        if self.is_async:
            await self.db.commit()
        else:
            self.db.commit()

        # Broadcast deletion
        try:
            await connection_manager.send_message(
                {"type": "message_deleted", "message_id": message_id}, message.session_id
            )
        except Exception as e:
            # Log but don't fail the deletion
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Failed to broadcast message deletion: %s", e)

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
        try:
            await connection_manager.send_message(
                {
                    "type": "message",
                    "message": {
                        "id": message.id,
                        "content": message.content,
                        "role": message.role,
                        "user_id": message.user_id,
                        "created_at": message.created_at.isoformat(),
                        "code_snippets": message.code_snippets,
                        "referenced_files": message.referenced_files,
                        "referenced_chunks": message.referenced_chunks,
                        # RAG metadata for frontend
                        "metadata": {
                            "ragUsed": message.rag_used,
                            "ragConfidence": float(message.rag_confidence) if message.rag_confidence else None,
                            "knowledgeSourcesCount": message.knowledge_sources_count,
                            "searchQuery": message.search_query_used,
                            "contextTokensUsed": message.context_tokens_used,
                            "ragStatus": message.rag_status,
                            "ragError": message.rag_error_message,
                        },
                    },
                },
                message.session_id,
            )
        except Exception as e:
            # Log but don't fail the operation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Failed to broadcast message: %s", e)

    async def _broadcast_message_update(self, message: ChatMessage):
        """Broadcast message edit."""
        try:
            await connection_manager.send_message(
                {
                    "type": "message_updated",
                    "message": {
                        "id": message.id,
                        "content": message.content,
                        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
                    },
                },
                message.session_id,
            )
        except Exception as e:
            # Log but don't fail the operation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Failed to broadcast message update: %s", e)

