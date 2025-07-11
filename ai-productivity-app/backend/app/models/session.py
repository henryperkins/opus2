"""Session model for JWT token tracking and management"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timezone


class Session(Base):
    """Active JWT session tracking"""

    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("jti", name="uq_sessions_jti"),
        # PostgreSQL-specific optimizations
        Index("idx_sessions_user_created", "user_id", "created_at"),
        Index(
            "idx_sessions_active",
            "user_id",
            "created_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index("idx_sessions_metadata_gin", "session_metadata", postgresql_using="gin"),
        # Check constraints
        CheckConstraint("char_length(jti) BETWEEN 40 AND 50", name="jti_length_valid"),
        CheckConstraint("created_at IS NOT NULL", name="created_at_not_null"),
        CheckConstraint(
            "jsonb_typeof(session_metadata) = 'object'",
            name="session_metadata_is_object",
        ),
        {
            "extend_existing": True,
        },
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who owns this session",
    )
    jti = Column(String(64), nullable=False, comment="JWT ID claim (unique per token)")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When the session was created",
    )
    revoked_at = Column(
        DateTime, nullable=True, comment="If not null, token has been revoked"
    )

    # Session metadata as JSONB for storing additional session information
    session_metadata = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Session metadata (IP address, user agent, etc.)",
    )

    # Relationships
    user = relationship("User", back_populates="sessions")

    @property
    def is_active(self) -> bool:
        """Check if session is still active (not revoked)"""
        return self.revoked_at is None

    def revoke(self) -> None:
        """Mark session as revoked"""
        self.revoked_at = datetime.now(timezone.utc)

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, jti='{self.jti}', active={self.is_active})>"
