"""Chat-related Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSessionCreate(BaseModel):
    """Create a new chat session."""
    project_id: int
    title: Optional[str] = Field(None, max_length=200)


class ChatSessionUpdate(BaseModel):
    """Update chat session."""
    title: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class MessageCreate(BaseModel):
    """Create a new message."""
    content: str = Field(..., min_length=1, max_length=10000)
    metadata: Optional[Dict[str, Any]] = None


class MessageUpdate(BaseModel):
    """Update existing message."""
    content: str = Field(..., min_length=1, max_length=10000)


class CodeSnippet(BaseModel):
    """Code snippet in a message."""
    language: str
    code: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class MessageResponse(BaseModel):
    """Message response model."""
    id: int
    session_id: int
    user_id: Optional[int]
    role: MessageRole
    content: str
    code_snippets: List[CodeSnippet] = []
    referenced_files: List[str] = []
    referenced_chunks: List[int] = []
    applied_commands: Dict[str, Any] = {}
    is_edited: bool = False
    edited_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    """Chat session response model."""
    id: int
    project_id: int
    title: str
    is_active: bool
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ChatSessionListResponse(BaseModel):
    """List of chat sessions."""
    items: List[ChatSessionResponse]
    total: int
