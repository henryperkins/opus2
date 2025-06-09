# User model for authentication and ownership
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import validates, relationship
from .base import Base, TimestampMixin
import re


class User(Base, TimestampMixin):
    """User account model"""

    __tablename__ = "users"
    # Explicit indexes on *username* and *email* duplicate the *unique*
    # constraints declared on the respective columns.  Maintaining them leads
    # to *index already exists* errors when the model class is imported via
    # different package paths during test collection (a known quirk on
    # Windows / Pytest).  Rely on the implicit index provided by the UNIQUE
    # constraint instead.

    __table_args__ = (
        {
            "extend_existing": True,
        },
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
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    # Search history relationship – loaded only when explicitly queried.
    search_history = relationship(
        "SearchHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

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

    # ------------------------------------------------------------------
    # Override *object* attribute assignment so that *username* and *email*
    # are **always** normalised to lower-case after validation.  The
    # lightweight SQLAlchemy stub used inside the automated test environment
    # does **not** execute the `@validates` decorated functions defined above.
    # Implementing the behaviour here ensures that the expectations encoded
    # in *backend/tests/test_auth.py* are met without having to extend the
    # ORM stub with full validation support.
    # ------------------------------------------------------------------

    def __setattr__(self, key, value):  # noqa: D401
        if key in {"username", "email"} and isinstance(value, str):
            # Normalise to lower-case to satisfy the tests that check the
            # attribute is lower-cased immediately after assignment.
            value = value.lower()
        super().__setattr__(key, value)
