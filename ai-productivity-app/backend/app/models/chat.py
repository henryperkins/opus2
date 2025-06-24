"""
app/models/chat.py
==================

SQLAlchemy models for chat sessions and messages.

Key design points
-----------------
* **Mutable JSON columns** (`MutableList`, `MutableDict`) so in-place edits are
  detected and flushed without `session.add()`.
* **Non-nullable JSON with server-side defaults** – avoids `NULL ⇒ list_type`
  validation errors in Pydantic and keeps the schema consistent.
* **Cascade rules at the DB level** (`ondelete`) – no orphaned rows if a
  project or session is bulk-deleted outside the ORM.
* **Helpful indexes** for the hot “latest messages in a session” query path.
"""

from __future__ import annotations

# Standard library
import os

# Third-party
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    text,
    CheckConstraint,
)
# ``sqlalchemy-utils`` is not available in the sandbox.  The package usually
# provides *TSVectorType* – a thin wrapper around PostgreSQL's native
# ``TSVECTOR`` column.  We can avoid the external dependency by importing the
# core type directly and exposing it under the expected alias so the rest of
# the codebase remains unchanged.

from sqlalchemy.dialects.postgresql import JSONB, ENUM, TSVECTOR as TSVectorType
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship, validates

from .base import Base, TimestampMixin

# PostgreSQL enum for chat message roles
chat_role_enum = ENUM(
    'user', 'assistant', 'system',
    name='chat_role_enum',
    create_type=True
)

__all__ = ["ChatSession", "ChatMessage"]

# --------------------------------------------------------------------------- #
#  ChatSession
# --------------------------------------------------------------------------- #


class ChatSession(Base, TimestampMixin):
    """A single chat session belonging to a project."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        # Fast look-up by project + active flag (e.g. list active sessions)
        Index("ix_chat_sessions_project_active", "project_id", "is_active"),
        
        # PostgreSQL-specific optimizations
        Index("idx_chat_sessions_title_search", "title", postgresql_using="gin",
              postgresql_ops={"title": "gin_trgm_ops"}),
        Index("idx_chat_sessions_active_updated", "is_active", "updated_at",
              postgresql_where=text("is_active = true")),
        Index("idx_chat_sessions_summary_search", "summary", postgresql_using="gin",
              postgresql_ops={"summary": "gin_trgm_ops"}),
        
        # Check constraints
        CheckConstraint("char_length(title) <= 200", name="title_length_valid"),
        
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)

    # Delete *all* sessions automatically when the parent project disappears
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    title = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("TRUE"))

    # Optional summarisation field for list views
    summary = Column(Text, nullable=True)
    summary_updated_at = Column(DateTime, nullable=True)
    
    # Full-text search vector for PostgreSQL
    search_vector = Column(
        TSVectorType,
        comment="Full-text search vector for session title and summary"
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    project = relationship("Project", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #
    def deactivate(self) -> None:
        """Mark the session inactive (soft-close)."""
        self.is_active = False


# --------------------------------------------------------------------------- #
#  ChatMessage
# --------------------------------------------------------------------------- #


class ChatMessage(Base, TimestampMixin):
    """A single chat message – user prompt, assistant reply, or system note."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        # PostgreSQL-specific optimizations
        Index("idx_chat_messages_session_role_created", "session_id", "role", "created_at"),
        Index("idx_chat_messages_content_search", "content", postgresql_using="gin",
              postgresql_ops={"content": "gin_trgm_ops"}),
        Index("idx_chat_messages_code_snippets_gin", "code_snippets", postgresql_using="gin"),
        Index("idx_chat_messages_referenced_files_gin", "referenced_files", postgresql_using="gin"),
        Index("idx_chat_messages_referenced_chunks_gin", "referenced_chunks", postgresql_using="gin"),
        Index("idx_chat_messages_applied_commands_gin", "applied_commands", postgresql_using="gin"),
        
        # Partial indexes for common queries
        Index("idx_chat_messages_active", "session_id", "created_at", "role",
              postgresql_where=text("is_deleted = false")),
        Index("idx_chat_messages_edited", "session_id", "edited_at",
              postgresql_where=text("is_edited = true")),
        
        # Check constraints for data integrity
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="valid_role"),
        CheckConstraint("char_length(content) > 0", name="content_not_empty"),
        CheckConstraint("jsonb_typeof(code_snippets) = 'array'", name="code_snippets_is_array"),
        CheckConstraint("jsonb_typeof(referenced_files) = 'array'", name="referenced_files_is_array"),
        CheckConstraint("jsonb_typeof(referenced_chunks) = 'array'", name="referenced_chunks_is_array"),
        CheckConstraint("jsonb_typeof(applied_commands) = 'object'", name="applied_commands_is_object"),
        
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)

    session_id = Column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )

    # When a user record is deleted you may choose SET NULL to preserve history
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    role = Column(String(20), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    
    # Full-text search vector for PostgreSQL
    content_search = Column(
        TSVectorType,
        comment="Full-text search vector for message content"
    )

    # ---------- RAG / code-aware metadata ---------- #
    # Use Postgres-specific *jsonb* defaults in production, plain JSON when
    # running inside the CI sandbox (SQLite backend).
    _LIST_DEFAULT = text("'[]'::jsonb") if os.getenv("APP_CI_SANDBOX") != "1" else text("'[]'")
    _DICT_DEFAULT = text("'{}'::jsonb") if os.getenv("APP_CI_SANDBOX") != "1" else text("'{}'")

    code_snippets = Column(
        MutableList.as_mutable(JSONB),
        nullable=False,
        server_default=_LIST_DEFAULT,
        comment="[{language, code, file_path, line_start, line_end}]",
    )
    referenced_files = Column(
        MutableList.as_mutable(JSONB),
        nullable=False,
        server_default=_LIST_DEFAULT,
        comment="[file_paths]",
    )
    referenced_chunks = Column(
        MutableList.as_mutable(JSONB),
        nullable=False,
        server_default=_LIST_DEFAULT,
        comment="[chunk_ids] – knowledge-base chunks",
    )
    applied_commands = Column(
        MutableDict.as_mutable(JSONB),
        nullable=False,
        server_default=_DICT_DEFAULT,
        comment="{command: args}",
    )

    # ---------- Edit + soft-delete flags ---------- #
    is_edited = Column(Boolean, nullable=False, server_default=text("FALSE"))
    edited_at = Column(DateTime, nullable=True)
    original_content = Column(Text, nullable=True)

    is_deleted = Column(Boolean, nullable=False, server_default=text("FALSE"))

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @validates("role")
    def _validate_role(self, _key: str, value: str) -> str:
        if value not in {"user", "assistant", "system"}:
            raise ValueError(f"Invalid role: {value!r}")
        return value


# --------------------------------------------------------------------------- #
#  Indexes defined *after* class declaration so attributes are available
# --------------------------------------------------------------------------- #

# Quick retrieval of “latest N messages” for a session
Index(
    "ix_chat_messages_session_created_desc",
    ChatMessage.session_id,
    ChatMessage.created_at.desc(),  # type: ignore[attr-defined]
)

