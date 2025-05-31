# User model for authentication and ownership
from sqlalchemy import Column, Integer, String, Boolean, Index, DateTime
from sqlalchemy.orm import validates, relationship
from .base import Base, TimestampMixin
import re


class User(Base, TimestampMixin):
    """User account model"""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_user_username", "username"),
        Index("idx_user_email", "email"),
    )

    id = Column(Integer, primary_key=True)
    username = Column(
        String(50), unique=True, nullable=False, comment="Unique username for login"
    )
    email = Column(
        String(100), unique=True, nullable=False, comment="User email address"
    )
    password_hash = Column(String(255), nullable=False, comment="Bcrypt password hash")
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Whether user account is active"
    )
    # Track most recent successful login (used by auth.utils.create_session)
    last_login = Column(
        DateTime,
        nullable=True,
        comment="Most recent successful login (UTC)",
    )

    # Relationships
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

    @validates("username")
    def validate_username(self, key, username):
        """Validate username format"""
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", username):
            raise ValueError(
                "Username can only contain letters, numbers, underscore, and hyphen"
            )
        return username.lower()

    @validates("email")
    def validate_email(self, key, email):
        """Validate email format"""
        if not email or "@" not in email:
            raise ValueError("Invalid email address")
        return email.lower()

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
