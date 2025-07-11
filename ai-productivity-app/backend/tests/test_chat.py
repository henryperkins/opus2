"""Test chat functionality, especially JSON field defaults."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.project import Project
from app.models.user import User
from app.schemas.chat import MessageResponse


@pytest.fixture
def test_user(db: Session):
    """Create a test user."""
    user = User(
        username="testuser", email="test@example.com", password_hash="hashedpassword"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_project(db: Session, test_user: User):
    """Create a test project."""
    project = Project(
        title="Test Project", description="A test project", owner_id=test_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_create_message_with_defaults(
    client: TestClient, db: Session, test_user: User, test_project: Project
):
    """Test creating a message ensures all JSON fields have default values."""
    # Create a chat session first
    session = ChatSession(project_id=test_project.id, title="Test Session")
    db.add(session)
    db.commit()

    # Create message via API
    response = client.post(
        f"/api/chat/sessions/{session.id}/messages",
        json={"content": "ping"},
        headers={"Authorization": "Bearer fake_token"},
    )

    assert response.status_code == 201
    data = response.json()

    # Verify all JSON fields have empty defaults, not None
    assert data["referenced_chunks"] == []
    assert data["referenced_files"] == []
    assert data["code_snippets"] == []
    assert data["applied_commands"] == {}


def test_message_response_from_orm_with_none_values(db: Session, test_project: Project):
    """Test that MessageResponse.from_orm() handles None values gracefully."""
    # Create a session
    session = ChatSession(project_id=test_project.id, title="Test Session")
    db.add(session)
    db.commit()

    # Create a message with explicit None values (simulating old data)
    message = ChatMessage(
        session_id=session.id,
        role="user",
        content="test message",
        code_snippets=None,
        referenced_files=None,
        referenced_chunks=None,
        applied_commands=None,
    )
    db.add(message)
    db.commit()

    # This should not raise a ValidationError
    response = MessageResponse.from_orm(message)

    # Verify defaults were applied
    assert response.referenced_chunks == []
    assert response.referenced_files == []
    assert response.code_snippets == []
    assert response.applied_commands == {}


def test_create_message_with_explicit_empty_lists(
    client: TestClient, db: Session, test_user: User, test_project: Project
):
    """Test creating a message with explicit empty values works correctly."""
    # Create a chat session first
    session = ChatSession(project_id=test_project.id, title="Test Session")
    db.add(session)
    db.commit()

    # Create message with metadata containing empty lists
    response = client.post(
        f"/api/chat/sessions/{session.id}/messages",
        json={
            "content": "test with metadata",
            "metadata": {
                "code_snippets": [],
                "referenced_files": [],
                "referenced_chunks": [],
                "commands": {},
            },
        },
        headers={"Authorization": "Bearer fake_token"},
    )

    assert response.status_code == 201
    data = response.json()

    # Verify all JSON fields are empty arrays/objects
    assert data["referenced_chunks"] == []
    assert data["referenced_files"] == []
    assert data["code_snippets"] == []
    assert data["applied_commands"] == {}


def test_database_defaults_after_migration(db: Session, test_project: Project):
    """Test that database-level defaults work for new records."""
    # Create a session
    session = ChatSession(project_id=test_project.id, title="Test Session")
    db.add(session)
    db.commit()

    # Create message without specifying JSON fields (they should get defaults)
    message = ChatMessage(session_id=session.id, role="user", content="test message")
    db.add(message)
    db.commit()
    db.refresh(message)

    # Verify database returned empty lists/objects, not None
    assert message.referenced_chunks == []
    assert message.referenced_files == []
    assert message.code_snippets == []
    assert message.applied_commands == {}


def test_websocket_message_serialization(db: Session, test_project: Project):
    """Test that WebSocket message serialization handles None values."""
    from app.websocket.handlers import serialize_message

    # Create a session
    session = ChatSession(project_id=test_project.id, title="Test Session")
    db.add(session)
    db.commit()

    # Create message with None values (simulating old data)
    message = ChatMessage(
        session_id=session.id,
        role="user",
        content="test message",
        code_snippets=None,
        referenced_files=None,
        referenced_chunks=None,
        applied_commands=None,
    )
    db.add(message)
    db.commit()

    # Serialize message (should not fail)
    serialized = serialize_message(message)

    # Verify None values were converted to empty lists/objects
    assert serialized["referenced_chunks"] == []
    assert serialized["referenced_files"] == []
    assert serialized["code_snippets"] == []
    assert serialized["applied_commands"] == {}
