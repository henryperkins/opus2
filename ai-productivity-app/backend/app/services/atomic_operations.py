# backend/app/services/atomic_operations.py
"""Service layer with atomic operations."""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.database.transactions import atomic
from app.models.project import Project, ProjectStatus
from app.models.session import Session as UserSession
from app.models.timeline import TimelineEvent
from app.models.user import User

logger = logging.getLogger(__name__)


class AtomicUserService:
    """User operations with transaction safety."""

    @staticmethod
    @atomic
    async def create_user_with_session(
        db: Session,
        username: str,
        email: str,
        password_hash: str,
        jti: str
    ) -> User:
        """Create user and session in single transaction."""
        # Create user
        user = User(
            username=username.lower(),
            email=email.lower(),
            password_hash=password_hash
        )
        db.add(user)
        db.flush()  # Get user.id without committing

        # Create session
        session = UserSession(
            user_id=user.id,
            jti=jti
        )
        db.add(session)

        # Both will be committed together
        return user

    @staticmethod
    @atomic
    async def delete_user_cascade(db: Session, user_id: int) -> bool:
        """Delete user and all related data atomically."""
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return False

        # Delete in correct order to avoid FK violations
        # Sessions
        db.query(UserSession).filter_by(user_id=user_id).delete()

        # Timeline events
        db.query(TimelineEvent).filter_by(user_id=user_id).delete()

        # Projects (will cascade to chat sessions, etc.)
        db.query(Project).filter_by(owner_id=user_id).delete()

        # Finally, the user
        db.delete(user)

        return True


class AtomicProjectService:
    """Project operations with transaction safety."""

