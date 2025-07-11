"""Pydantic schemas for project management.

Provides request/response models for project CRUD operations,
timeline events, and filtering.
"""

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Compatibility shim – *pydantic* v1.x does not provide ``field_validator``
# which was introduced in v2.  Older versions only have ``validator``.
# Create an alias so that the same decorator name works in both versions.
# ---------------------------------------------------------------------------

try:
    from pydantic import field_validator  # type: ignore
except ImportError:  # pragma: no cover – running on Pydantic < 2
    from pydantic import validator as field_validator  # type: ignore
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    """Project status enumeration."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class ProjectBase(BaseModel):
    """Base project schema."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    color: Optional[str] = Field("#3B82F6", pattern="^#[0-9A-Fa-f]{6}$")
    emoji: Optional[str] = Field("📁", max_length=10)
    tags: List[str] = Field(default_factory=list, max_items=20)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate and clean tags."""
        cleaned = []
        for tag in v:
            tag = tag.strip().lower()
            if tag and len(tag) <= 50 and tag not in cleaned:
                cleaned.append(tag)
        return cleaned


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    status: ProjectStatus = ProjectStatus.ACTIVE


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ProjectStatus] = None
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    emoji: Optional[str] = Field(None, max_length=10)
    tags: Optional[List[str]] = Field(None, max_items=20)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and clean tags if provided."""
        if v is None:
            return None
        cleaned = []
        for tag in v:
            tag = tag.strip().lower()
            if tag and len(tag) <= 50 and tag not in cleaned:
                cleaned.append(tag)
        return cleaned


class UserInfo(BaseModel):
    """Minimal user information."""

    id: int
    username: str
    email: str


class ProjectStats(BaseModel):
    """Project statistics."""

    files: int = 0
    timeline_events: int = 0
    last_activity: Optional[datetime] = None


class ProjectResponse(ProjectBase):
    """Complete project response."""

    id: int
    status: ProjectStatus
    owner: UserInfo
    created_at: datetime
    updated_at: datetime
    stats: Optional[ProjectStats] = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Paginated project list response."""

    items: List[ProjectResponse]
    total: int
    page: int = 1
    per_page: int = 20


class TimelineEventType(str, Enum):
    """Timeline event types."""

    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    FILE_ADDED = "file_added"
    FILE_REMOVED = "file_removed"
    MILESTONE = "milestone"
    COMMENT = "comment"
    CHAT_CREATED = "chat_created"
    CHAT_MESSAGE = "chat_message"


class TimelineEventCreate(BaseModel):
    """Schema for creating a timeline event."""

    event_type: TimelineEventType
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TimelineEventResponse(BaseModel):
    """Timeline event response."""

    id: int
    project_id: int
    event_type: TimelineEventType
    title: str
    description: Optional[str]
    metadata: Dict[str, Any]
    user: Optional[UserInfo]
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectFilters(BaseModel):
    """Project filtering options."""

    status: Optional[ProjectStatus] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = Field(None, max_length=100)
    owner_id: Optional[int] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
