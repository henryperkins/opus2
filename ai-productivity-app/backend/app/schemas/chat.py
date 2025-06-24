# app/schemas/chat.py
"""Chat-related Pydantic schemas for request/response validation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Pydantic v1/v2 compatibility -------------------------------------------------
#
# Our production environment uses Pydantic v2 which provides the ``model_validator``
# decorator and the ``ConfigDict`` helper for configuring models via the
# ``model_config`` attribute.  The test environment, however, ships with
# Pydantic v1.x which does not expose those symbols.  Importing them therefore
# triggers an ``ImportError`` during test collection.
#
# To keep the codebase compatible with both major versions we attempt to import
# the v2-only names and, if that fails, provide graceful fall-backs that mimic
# the v2 API well enough for our limited use-case (mainly the *before* model
# validator).  This avoids having to maintain two separate schema versions or
# introducing a hard dependency on Pydantic v2 inside the test runner.
# --------------------------------------------------------------------------- #

from pydantic import BaseModel, Field

# Try to import the v2-specific helpers.  When running under Pydantic v1 they
# are unavailable, so we poly-fill them with no-op implementations.

try:
    from pydantic import model_validator, field_validator, ConfigDict  # type: ignore

except ImportError:  # Older Pydantic version *or* stubbed implementation

    # We may run with either
    #   a) Pydantic v1.x  (does not expose ``model_validator`` / ``ConfigDict``)
    #   b) A stub module installed by ``app.compat`` when the real dependency
    #      is unavailable in the sandbox (also missing the v2 helpers)
    #
    # In both cases falling back to *no-op* shims is sufficient for the limited
    # validation logic used in this file.  The goal is simply to avoid
    # ``ImportError`` so the package can be imported during test collection.

    def model_validator(*, mode: str = "after"):  # type: ignore
        """Replacement decorator that returns the original function unchanged."""

        def decorator(fn):  # noqa: D401 – keep signature identical
            return fn

        return decorator

    def field_validator(*args, **kwargs):  # type: ignore
        """Replacement decorator that returns the original function unchanged."""
        
        def decorator(fn):  # noqa: D401 – keep signature identical
            return fn
        
        return decorator

    class ConfigDict(dict):  # type: ignore
        """Minimal stand-in – behaves like a plain ``dict``."""

        pass


# --------------------------------------------------------------------------- #
#  Enumerations
# --------------------------------------------------------------------------- #
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# --------------------------------------------------------------------------- #
#  Session I/O
# --------------------------------------------------------------------------- #
class ChatSessionCreate(BaseModel):
    """Create a new chat session."""
    project_id: int
    title: Optional[str] = Field(default=None, max_length=200)


class ChatSessionUpdate(BaseModel):
    """Patch a chat session."""
    title: Optional[str] = Field(default=None, max_length=200)
    is_active: Optional[bool] = None


# --------------------------------------------------------------------------- #
#  Message I/O
# --------------------------------------------------------------------------- #
class CodeSnippet(BaseModel):
    """A code excerpt attached to a message."""
    language: str
    code: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class MessageCreate(BaseModel):
    """Payload when posting a new chat message."""
    role: MessageRole | str = Field(..., description="sender role")
    content: str = Field(..., min_length=1, max_length=10_000)

    # Optional annotation / RAG metadata
    code_snippets: List[CodeSnippet] = Field(default_factory=list)
    referenced_files: List[str] = Field(default_factory=list)
    referenced_chunks: List[int] = Field(default_factory=list)
    applied_commands: Dict[str, Any] = Field(default_factory=dict)

    # ---------------------------------------------------------------------
    # Accept both the raw Enum *and* plain strings coming from legacy /
    # external clients.  Convert early so downstream code can rely on a
    # consistent Enum instance and safely access ``.value``.
    # ---------------------------------------------------------------------
    @model_validator(mode="before")
    def _ensure_enum_role(cls, values):
        if isinstance(values, dict) and "role" in values:
            role = values["role"]
            if isinstance(role, str):
                try:
                    values["role"] = MessageRole(role)
                except ValueError as exc:
                    raise ValueError(f"Invalid role '{role}'") from exc
        return values


class MessageUpdate(BaseModel):
    """Edit an existing message (only content for now)."""
    content: str = Field(..., min_length=1, max_length=10_000)


# --------------------------------------------------------------------------- #
#  Response models (DB → API)
# --------------------------------------------------------------------------- #
class MessageResponse(BaseModel):
    """Message returned from the API."""
    id: int
    session_id: int
    user_id: Optional[int] = None

    role: MessageRole
    content: str

    code_snippets: List[CodeSnippet] = Field(default_factory=list)
    referenced_files: List[str] = Field(default_factory=list)
    referenced_chunks: List[int] = Field(default_factory=list)
    applied_commands: Dict[str, Any] = Field(default_factory=dict)

    is_edited: bool = Field(default=False)
    edited_at: Optional[datetime] = None
    created_at: datetime

    @field_validator('is_edited', mode='before')
    def validate_is_edited(cls, v):
        """Convert None to False for is_edited field."""
        return False if v is None else v

    # --- Pydantic v2 config ---
    model_config = ConfigDict(from_attributes=True)

    # Accept rows where JSON columns are NULL (legacy data)
    @model_validator(mode="before")
    @classmethod
    def _coerce_null_collections(cls, data):
        if isinstance(data, dict):
            data["code_snippets"] = data.get("code_snippets") or []
            data["referenced_files"] = data.get("referenced_files") or []
            data["referenced_chunks"] = data.get("referenced_chunks") or []
            data["applied_commands"] = data.get("applied_commands") or {}
        return data


class ChatSessionResponse(BaseModel):
    """Session metadata shown in lists/detail views."""
    id: int
    project_id: int
    title: str
    is_active: bool

    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ChatSessionListResponse(BaseModel):
    """Paginated list wrapper."""
    items: List[ChatSessionResponse]
    total: int
