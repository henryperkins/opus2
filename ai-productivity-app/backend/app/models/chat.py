from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, Boolean, DateTime, Index
from sqlalchemy.orm import relationship, validates
from .base import Base, TimestampMixin
import json


class ChatSession(Base, TimestampMixin):
    """Chat session for a project with AI assistance."""

    __tablename__ = 'chat_sessions'
    __table_args__ = (
        Index("idx_chat_session_project", "project_id"),
        Index("idx_chat_session_updated", "updated_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    title = Column(String(200))
    is_active = Column(Boolean, default=True)

    # Summary for quick overview
    summary = Column(Text)
    summary_updated_at = Column(DateTime)

    # Relationships
    project = relationship("Project", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base, TimestampMixin):
    """Individual message in a chat session."""

    __tablename__ = 'chat_messages'
    __table_args__ = (
        Index("idx_chat_message_session", "session_id"),
        Index("idx_chat_message_created", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Code awareness
    code_snippets = Column(JSON)  # [{language, code, file_path, line_start, line_end}]
    referenced_files = Column(JSON)  # [file_paths]
    referenced_chunks = Column(JSON)  # [chunk_ids] from semantic search
    applied_commands = Column(JSON)  # {command: args}

    # Edit tracking
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime)
    original_content = Column(Text)  # Store original if edited

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")

    @validates("role")
    def validate_role(self, key, role):
        valid_roles = {'user', 'assistant', 'system'}
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}")
        return role
