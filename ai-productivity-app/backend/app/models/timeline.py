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
    #
    # NOTE:
    # -----
    # During the test-suite collection phase the *app* package can be imported
    # multiple times via different `sys.path` entries (e.g. once as
    # ``ai-productivity-app.backend.app`` and again as the plain ``app``
    # package).  When that happens SQLAlchemy ends up evaluating this model
    # definition twice which normally results in the
    # *Table 'timeline_events' is already defined* error.  By adding the
    # ``extend_existing=True`` flag we instruct SQLAlchemy to quietly reuse the
    # first table object instead of raising, making the declaration idempotent
    # and safe under repeated imports.
    #
    __table_args__ = (
        {"extend_existing": True},
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
    # Chat specific events (Phase-5)
    EVENT_CHAT_CREATED = "chat_created"

    @validates("event_type")
    def validate_event_type(self, key, event_type):
        """Validate event type."""
        # List of accepted event type strings.
        valid_types = [
            self.EVENT_CREATED,
            self.EVENT_UPDATED,
            self.EVENT_STATUS_CHANGED,
            self.EVENT_FILE_ADDED,
            self.EVENT_FILE_REMOVED,
            self.EVENT_MILESTONE,
            self.EVENT_COMMENT,
            self.EVENT_CHAT_CREATED,
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
