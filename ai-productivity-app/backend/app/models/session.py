"""Session model for JWT token tracking and management"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime, timezone


class Session(Base):
    """Active JWT session tracking"""

    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("jti", name="uq_sessions_jti"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        comment="User who owns this session"
    )
    jti = Column(
        String(64), 
        nullable=False, 
        comment="JWT ID claim (unique per token)"
    )
    created_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False,
        comment="When the session was created"
    )
    revoked_at = Column(
        DateTime, 
        nullable=True, 
        comment="If not null, token has been revoked"
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