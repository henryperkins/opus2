"""Project model with enhanced features for organizing work.

Includes status tracking, visual customization (color/emoji), tags,
and relationship to timeline events for comprehensive project management.
"""
from sqlalchemy import Column, Integer, String, Text, Enum, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.mutable import MutableList
from .base import Base, TimestampMixin
import enum
import re


class ProjectStatus(enum.Enum):
    """Project status enumeration."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class Project(Base, TimestampMixin):
    """Project model for organizing code and chat sessions."""

    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_project_owner", "owner_id"),
        Index("idx_project_status", "status"),
        Index("idx_project_created", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    title = Column(
        String(200),
        nullable=False,
        comment="Project title"
    )
    description = Column(
        Text,
        comment="Project description"
    )
    status = Column(
        Enum(ProjectStatus),
        default=ProjectStatus.ACTIVE,
        nullable=False,
        comment="Project status"
    )
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who created the project"
    )

    # Visual customization
    color = Column(
        String(7),
        default="#3B82F6",
        comment="Hex color for project"
    )
    emoji = Column(
        String(10),
        default="📁",
        comment="Emoji for project"
    )

    # Metadata
    tags = Column(
        MutableList.as_mutable(JSON),
        default=list,
        comment="Project tags"
    )

    # Relationships
    owner = relationship("User", back_populates="projects")
    timeline_events = relationship(
        "TimelineEvent",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="desc(TimelineEvent.created_at)"
    )

    @validates("title")
    def validate_title(self, key, title):
        """Validate project title."""
        if not title or len(title.strip()) == 0:
            raise ValueError("Project title cannot be empty")
        if len(title) > 200:
            raise ValueError("Project title cannot exceed 200 characters")
        return title.strip()

    @validates("color")
    def validate_color(self, key, color):
        """Validate hex color format."""
        if color and not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            raise ValueError("Color must be a valid hex color (e.g., #3B82F6)")
        return color

    @validates("tags")
    def validate_tags(self, key, tags):
        """Validate tags list."""
        if not isinstance(tags, list):
            raise ValueError("Tags must be a list")
        # Ensure all tags are strings and strip whitespace
        cleaned_tags = []
        for tag in tags:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
            cleaned = tag.strip().lower()
            if cleaned and cleaned not in cleaned_tags:
                cleaned_tags.append(cleaned)
        return cleaned_tags

    @property
    def is_active(self):
        """Check if project is active."""
        return self.status == ProjectStatus.ACTIVE

    def can_modify(self, user_id: int) -> bool:
        """Check if user can modify project."""
        # For small team, all authenticated users can modify all projects
        return True

    def __repr__(self):
        return f"<Project(id={self.id}, title='{self.title}', status={self.status.value})>"
