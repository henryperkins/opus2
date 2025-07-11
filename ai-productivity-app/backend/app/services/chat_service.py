from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.chat import ChatSession, ChatMessage
from ..models.timeline import TimelineEvent
from ..websocket.manager import connection_manager

# Pydantic request models are not required inside the service layer


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
            knowledge_sources_count=(
                rag_metadata.get("knowledge_sources_count", 0) if rag_metadata else 0
            ),
            search_query_used=(
                rag_metadata.get("search_query_used") if rag_metadata else None
            ),
            context_tokens_used=(
                rag_metadata.get("context_tokens_used", 0) if rag_metadata else 0
            ),
            rag_status=rag_metadata.get("rag_status") if rag_metadata else None,
            rag_error_message=(
                rag_metadata.get("rag_error_message") if rag_metadata else None
            ),
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
                    ChatMessage.is_deleted.is_(False),
                )
            )
            message = result.scalar_one_or_none()
        else:
            message = (
                self.db.query(ChatMessage)
                .filter(
                    ChatMessage.id == message_id,
                    ChatMessage.user_id == user_id,
                    ChatMessage.is_deleted.is_(False),
                )
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
        self,
        message_id: int,
        content: str,
        code_snippets: Optional[List[Dict[str, Any]]] = None,
        broadcast: bool = True,
    ) -> Optional[ChatMessage]:
        """Update message content and code snippets (for AI messages)."""
        if self.is_async:
            result = await self.db.execute(
                select(ChatMessage).where(
                    ChatMessage.id == message_id, ChatMessage.is_deleted.is_(False)
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

    async def delete_message(
        self, message_id: int, _user_id: int
    ) -> bool:  # noqa: D401 – keep signature for BC
        """Soft-delete *any* message by ``message_id``.

        The caller is responsible for *authorisation*.  This method merely
        performs the state change and broadcasts the deletion.  It returns
        ``True`` when the message existed (even if already deleted) and the
        operation succeeded, otherwise ``False``.
        """
        # Fetch without filtering on *user_id* – permission is checked in router.
        if self.is_async:
            result = await self.db.execute(
                select(ChatMessage).where(ChatMessage.id == message_id)
            )
            message = result.scalar_one_or_none()
        else:
            message = self.db.query(ChatMessage).filter_by(id=message_id).first()

        if not message:
            return False
        if message.is_deleted:
            return True  # already deleted – treat as success

        message.is_deleted = True

        if self.is_async:
            await self.db.commit()
        else:
            self.db.commit()

        # Broadcast deletion
        try:
            await connection_manager.send_message(
                {"type": "message_deleted", "message_id": message_id},
                message.session_id,
            )
        except Exception as e:
            # Log but don't fail the deletion
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("Failed to broadcast message deletion: %s", e)

        return True

    async def get_session_messages(
        self, session_id: int, limit: int = 50, before_id: Optional[int] = None
    ) -> List[ChatMessage]:
        """Return up to *limit* most recent messages for *session_id*.

        Behaviour:
        • When *before_id* is ``None`` (initial page load) the **latest**
          ``limit`` messages are returned so the user always sees the most
          recent conversation after a reload.
        • When *before_id* is provided (pagination while scrolling **up**) we
          fetch the next *older* batch.  The consumer expects messages in
          chronological order (old → new) therefore the slice is first ordered
          *descending* to efficiently grab the window and then reversed before
          returning.
        """

        # In Postgres a boolean column is always stored as the *real* boolean
        # type so we can use a straight *is False* comparison.  Legacy support
        # for the SQLite string literal `'FALSE'` has been dropped because the
        # application now runs exclusively on PostgreSQL (Neon).  Keeping the
        # check would create an implicit cast in Postgres and hurt index
        # usage.
        not_deleted_filter = ChatMessage.is_deleted.is_(False)

        def _reverse_if_needed(rows):
            """Helper to ensure ascending chronological order."""
            # Rows are reversed **only** when they were fetched in DESC order.
            return list(reversed(rows))

        if self.is_async:
            base_query = select(ChatMessage).where(
                ChatMessage.session_id == session_id,
                not_deleted_filter,
            )

            if before_id is None:
                # Latest page – order DESC to grab most recent, then reverse
                # to maintain chronological order.
                query = base_query.order_by(ChatMessage.created_at.desc()).limit(limit)
                result = await self.db.execute(query)
                rows = result.scalars().all()
                return _reverse_if_needed(rows)

            # Pagination – fetch messages **older** than *before_id*.
            query = (
                base_query.where(ChatMessage.id < before_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            result = await self.db.execute(query)
            rows = result.scalars().all()
            return _reverse_if_needed(rows)

        # ---------------------- synchronous (non-async) path -----------------

        base_query = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .filter(not_deleted_filter)
        )

        if before_id is None:
            rows = base_query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
            return _reverse_if_needed(rows)

        rows = (
            base_query.filter(ChatMessage.id < before_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return _reverse_if_needed(rows)

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
                            "ragConfidence": (
                                float(message.rag_confidence)
                                if message.rag_confidence
                                else None
                            ),
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
                        "edited_at": (
                            message.edited_at.isoformat() if message.edited_at else None
                        ),
                    },
                },
                message.session_id,
            )
        except Exception as e:
            # Log but don't fail the operation
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("Failed to broadcast message update: %s", e)
