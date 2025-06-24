# backend/tests/test_atomic_transactions.py
"""Tests for atomic transaction operations."""
import pytest
from sqlalchemy.orm import Session
from app.database.transactions import atomic
from app.services.atomic_operations import (
    AtomicProjectService, AtomicUserService
)
from app.models.project import Project
from app.models.timeline import TimelineEvent
from app.models.user import User
from app.models.session import Session as UserSession


def test_atomic_decorator_commits_on_success(db: Session):
    """Test that atomic decorator commits on success."""
    initial_count = db.query(User).count()

    with atomic(db):
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed"
        )
        db.add(user)

    # Should be committed
    assert db.query(User).count() == initial_count + 1


def test_atomic_decorator_rolls_back_on_error(db: Session):
    """Test that atomic decorator rolls back on error."""
    initial_count = db.query(User).count()

    with pytest.raises(ValueError):
        with atomic(db):
            user = User(
                username="testuser",
                email="test@example.com",
                password_hash="hashed"
            )
            db.add(user)
            raise ValueError("Test error")

    # Should be rolled back
    assert db.query(User).count() == initial_count


@pytest.mark.asyncio
async def test_create_project_with_timeline_atomic(
    db: Session, test_user: User
):
    """Test project creation with timeline event is atomic."""
    initial_projects = db.query(Project).count()
    initial_events = db.query(TimelineEvent).count()

    project = await AtomicProjectService.create_project_with_timeline(
        db=db,
        title="Test Project",
        owner_id=test_user.id,
        description="Test description"
    )

    # Both project and timeline event should exist
    assert db.query(Project).count() == initial_projects + 1
    assert db.query(TimelineEvent).count() == initial_events + 1

    # Timeline event should reference the project
    event = db.query(TimelineEvent).filter_by(project_id=project.id).first()
    assert event is not None
    assert "Test Project" in event.title


@pytest.mark.asyncio
async def test_create_user_with_session_atomic(db: Session):
    """Test user creation with session is atomic."""
    initial_users = db.query(User).count()
    initial_sessions = db.query(UserSession).count()

    user = await AtomicUserService.create_user_with_session(
        db=db,
        username="newuser",
        email="new@example.com",
        password_hash="hashed",
        jti="test-jti"
    )

    # Both user and session should exist
    assert db.query(User).count() == initial_users + 1
    assert db.query(UserSession).count() == initial_sessions + 1

    # Session should reference the user
    session = db.query(UserSession).filter_by(user_id=user.id).first()
    assert session is not None
    assert session.jti == "test-jti"


@pytest.mark.asyncio
async def test_archive_project_atomic(
    db: Session, test_project: Project, test_user: User
):
    """Test project archival with timeline event is atomic."""
    initial_events = db.query(TimelineEvent).count()

    success = await AtomicProjectService.archive_project(
        db=db,
        project_id=test_project.id,
        user_id=test_user.id
    )

    assert success is True

    # Project should be archived
    db.refresh(test_project)
    assert test_project.status == "archived"

    # Timeline event should be created
    assert db.query(TimelineEvent).count() == initial_events + 1

    event = db.query(TimelineEvent).filter_by(
        project_id=test_project.id
    ).first()
    assert event is not None
    assert "archived" in event.title.lower()


@pytest.mark.asyncio
async def test_delete_user_cascade_atomic(db: Session, test_user: User):
    """Test cascading user deletion is atomic."""
    # Create some related data
    project = Project(
        title="Test Project",
        owner_id=test_user.id
    )
    db.add(project)
    db.flush()

    session = UserSession(
        user_id=test_user.id,
        jti="test-jti"
    )
    db.add(session)

    event = TimelineEvent(
        project_id=project.id,
        user_id=test_user.id,
        event_type="created",
        title="Test event"
    )
    db.add(event)
    db.commit()

    user_id = test_user.id

    # Delete user cascade
    success = await AtomicUserService.delete_user_cascade(
        db=db,
        user_id=user_id
    )

    assert success is True

    # All related data should be deleted
    assert db.query(User).filter_by(id=user_id).first() is None
    assert db.query(Project).filter_by(owner_id=user_id).first() is None
    assert db.query(UserSession).filter_by(user_id=user_id).first() is None
    assert db.query(TimelineEvent).filter_by(user_id=user_id).first() is None
