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
)
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import relationship, validates

from .base import Base, TimestampMixin

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

    # ---------- RAG / code-aware metadata ---------- #
    # Use Postgres-specific *jsonb* defaults in production, plain JSON when
    # running inside the CI sandbox (SQLite backend).
    _LIST_DEFAULT = text("'[]'::jsonb") if os.getenv("APP_CI_SANDBOX") != "1" else text("'[]'")
    _DICT_DEFAULT = text("'{}'::jsonb") if os.getenv("APP_CI_SANDBOX") != "1" else text("'{}'")

    code_snippets = Column(
        MutableList.as_mutable(JSON),
        nullable=False,
        server_default=_LIST_DEFAULT,
        comment="[{language, code, file_path, line_start, line_end}]",
    )
    referenced_files = Column(
        MutableList.as_mutable(JSON),
        nullable=False,
        server_default=_LIST_DEFAULT,
        comment="[file_paths]",
    )
    referenced_chunks = Column(
        MutableList.as_mutable(JSON),
        nullable=False,
        server_default=_LIST_DEFAULT,
        comment="[chunk_ids] – knowledge-base chunks",
    )
    applied_commands = Column(
        MutableDict.as_mutable(JSON),
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

