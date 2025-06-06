"""Timeline event model for tracking project history.

Records all significant events in a project's lifecycle including
creation, updates, file additions, and custom milestones.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship, validates
from .base import Base, TimestampMixin


class TimelineEvent(Base, TimestampMixin):
    """Timeline event for project activity tracking."""

    __tablename__ = "timeline_events"
    __table_args__ = (
        Index("idx_timeline_project", "project_id"),
        Index("idx_timeline_type", "event_type"),
        Index("idx_timeline_created", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="Associated project"
    )
    event_type = Column(
        String(50),
        nullable=False,
        comment="Type of event"
    )
    title = Column(
        String(200),
        nullable=False,
        comment="Event title"
    )
    description = Column(
        Text,
        comment="Detailed event description"
    )
    event_metadata = Column(
        "metadata",
        JSON,
        default=dict,
        comment="Event-specific data"
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who triggered the event"
    )

    # Relationships
    project = relationship("Project", back_populates="timeline_events")
    user = relationship("User")

    # Common event types
    EVENT_CREATED = "created"
    EVENT_UPDATED = "updated"
    EVENT_STATUS_CHANGED = "status_changed"
    EVENT_FILE_ADDED = "file_added"
    EVENT_FILE_REMOVED = "file_removed"
    EVENT_MILESTONE = "milestone"
    EVENT_COMMENT = "comment"

    @validates("event_type")
    def validate_event_type(self, key, event_type):
        """Validate event type."""
        valid_types = [
            self.EVENT_CREATED, self.EVENT_UPDATED, self.EVENT_STATUS_CHANGED,
            self.EVENT_FILE_ADDED, self.EVENT_FILE_REMOVED, self.EVENT_MILESTONE,
            self.EVENT_COMMENT
        ]
        if event_type not in valid_types:
            raise ValueError(
                f"Invalid event type. Must be one of: {', '.join(valid_types)}"
            )
        return event_type

    @validates("title")
    def validate_title(self, key, title):
        """Validate event title."""
        if not title or len(title.strip()) == 0:
            raise ValueError("Event title cannot be empty")
        if len(title) > 200:
            raise ValueError(
                "Event title cannot exceed 200 characters"
            )
        return title.strip()

    def __repr__(self):
        return (
            f"<TimelineEvent(id={self.id}, "
            f"type='{self.event_type}', project_id={self.project_id})>"
        )
