# Project model for organizing work
from sqlalchemy import Column, Integer, String, Text, Enum, Index, ForeignKey
from sqlalchemy.orm import validates
from .base import Base, TimestampMixin
import enum


class ProjectStatus(enum.Enum):
    """Project status enumeration"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class Project(Base, TimestampMixin):
    """Project model for organizing code and chat sessions"""

    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_project_owner", "owner_id"),
        Index("idx_project_status", "status"),
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

    @validates("title")
    def validate_title(self, key, title):
        """Validate project title"""
        if not title or len(title.strip()) == 0:
            raise ValueError("Project title cannot be empty")
        if len(title) > 200:
            raise ValueError("Project title cannot exceed 200 characters")
        return title.strip()

    def __repr__(self):
        return f"<Project(id={self.id}, title='{self.title}', status={self.status.value})>"
