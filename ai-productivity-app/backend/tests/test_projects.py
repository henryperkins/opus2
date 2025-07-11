"""Comprehensive tests for project management functionality."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from app.main import app
from app.models.project import Project, ProjectStatus
from app.models.timeline import TimelineEvent
from app.models.user import User
from app.database import get_db


@pytest.fixture
def test_user(db: Session):
    """Create a test user."""
    user = User(
        username="testuser", email="test@example.com", password_hash="hashed_password"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Get authentication headers."""
    # In real tests, this would generate a JWT token
    return {"Authorization": f"Bearer test_token_{test_user.id}"}


@pytest.fixture
def test_project(db: Session, test_user):
    """Create a test project."""
    project = Project(
        title="Test Project",
        description="Test Description",
        status=ProjectStatus.ACTIVE,
        owner_id=test_user.id,
        color="#3B82F6",
        emoji="🚀",
        tags=["test", "demo"],
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


class TestProjectCRUD:
    """Test project CRUD operations."""

    def test_create_project(self, client: TestClient, auth_headers):
        """Test creating a new project."""
        response = client.post(
            "/api/projects",
            json={
                "title": "New Project",
                "description": "Project description",
                "status": "active",
                "color": "#10B981",
                "emoji": "💡",
                "tags": ["backend", "api"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Project"
        assert data["status"] == "active"
        assert data["color"] == "#10B981"
        assert data["emoji"] == "💡"
        assert set(data["tags"]) == {"backend", "api"}
        assert "owner" in data
        assert "id" in data

    def test_create_project_invalid_data(self, client: TestClient, auth_headers):
        """Test creating project with invalid data."""
        response = client.post(
            "/api/projects",
            json={
                "title": "",  # Empty title
                "color": "invalid",  # Invalid color format
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_list_projects(self, client: TestClient, auth_headers, test_project):
        """Test listing projects."""
        response = client.get("/api/projects", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1
        assert data["total"] >= 1

    def test_list_projects_with_filters(
        self, client: TestClient, auth_headers, test_project
    ):
        """Test listing projects with filters."""
        # Test status filter
        response = client.get("/api/projects?status=active", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for project in data["items"]:
            assert project["status"] == "active"

        # Test tag filter
        response = client.get("/api/projects?tags=test", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1

        # Test search
        response = client.get("/api/projects?search=Test", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1

    def test_get_project(self, client: TestClient, auth_headers, test_project):
        """Test getting a single project."""
        response = client.get(f"/api/projects/{test_project.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_project.id
        assert data["title"] == test_project.title
        assert "stats" in data

    def test_get_nonexistent_project(self, client: TestClient, auth_headers):
        """Test getting a project that doesn't exist."""
        response = client.get("/api/projects/99999", headers=auth_headers)

        assert response.status_code == 404

    def test_update_project(self, client: TestClient, auth_headers, test_project):
        """Test updating a project."""
        response = client.put(
            f"/api/projects/{test_project.id}",
            json={
                "title": "Updated Title",
                "status": "completed",
                "tags": ["updated", "test"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "completed"
        assert set(data["tags"]) == {"updated", "test"}

    def test_delete_project(self, client: TestClient, auth_headers, test_project):
        """Test deleting a project."""
        response = client.delete(
            f"/api/projects/{test_project.id}", headers=auth_headers
        )

        assert response.status_code == 204

        # Verify project is deleted
        response = client.get(f"/api/projects/{test_project.id}", headers=auth_headers)
        assert response.status_code == 404

    def test_archive_project(self, client: TestClient, auth_headers, test_project):
        """Test archiving a project."""
        response = client.post(
            f"/api/projects/{test_project.id}/archive", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"


class TestTimelineEvents:
    """Test timeline event functionality."""

    def test_project_creates_initial_event(self, client: TestClient, auth_headers):
        """Test that creating a project creates an initial timeline event."""
        # Create project
        response = client.post(
            "/api/projects", json={"title": "Timeline Test"}, headers=auth_headers
        )
        project_id = response.json()["id"]

        # Get timeline
        response = client.get(
            f"/api/projects/{project_id}/timeline", headers=auth_headers
        )

        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        assert events[0]["event_type"] == "created"
        assert "Timeline Test" in events[0]["title"]

    def test_update_creates_timeline_event(
        self, client: TestClient, auth_headers, test_project
    ):
        """Test that updating a project creates timeline events."""
        # Update status
        response = client.put(
            f"/api/projects/{test_project.id}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Get timeline
        response = client.get(
            f"/api/projects/{test_project.id}/timeline", headers=auth_headers
        )

        events = response.json()
        status_events = [e for e in events if e["event_type"] == "status_changed"]
        assert len(status_events) >= 1
        assert status_events[0]["title"] == "Status changed to completed"

    def test_add_custom_timeline_event(
        self, client: TestClient, auth_headers, test_project
    ):
        """Test adding a custom timeline event."""
        response = client.post(
            f"/api/projects/{test_project.id}/timeline",
            json={
                "event_type": "milestone",
                "title": "Beta Release",
                "description": "Released beta version to testers",
                "metadata": {"version": "0.1.0"},
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "milestone"
        assert data["title"] == "Beta Release"
        assert data["metadata"]["version"] == "0.1.0"

    def test_timeline_pagination(
        self, client: TestClient, auth_headers, test_project, db: Session
    ):
        """Test timeline pagination."""
        # Add multiple events
        for i in range(10):
            event = TimelineEvent(
                project_id=test_project.id,
                event_type=TimelineEvent.EVENT_COMMENT,
                title=f"Comment {i}",
                user_id=test_project.owner_id,
            )
            db.add(event)
        db.commit()

        # Test limit
        response = client.get(
            f"/api/projects/{test_project.id}/timeline?limit=5", headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 5

        # Test offset
        response = client.get(
            f"/api/projects/{test_project.id}/timeline?limit=5&offset=5",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) >= 5


class TestProjectAuthorization:
    """Test project authorization."""

    def test_unauthorized_access(self, client: TestClient):
        """Test accessing projects without authentication."""
        response = client.get("/api/projects")
        assert response.status_code == 401

    def test_all_users_can_modify_projects(
        self, client: TestClient, auth_headers, test_project, db: Session
    ):
        """Test that all authenticated users can modify any project (small team feature)."""
        # Create another user
        other_user = User(
            username="otheruser", email="other@example.com", password_hash="hashed"
        )
        db.add(other_user)
        db.commit()

        # Use other user's auth (in real tests, generate new token)
        other_headers = {"Authorization": f"Bearer test_token_{other_user.id}"}

        # Other user should be able to update the project
        response = client.put(
            f"/api/projects/{test_project.id}",
            json={"title": "Updated by other user"},
            headers=other_headers,
        )

        # For small team, this should succeed
        assert response.status_code == 200


class TestProjectValidation:
    """Test project data validation."""

    def test_title_validation(self, client: TestClient, auth_headers):
        """Test project title validation."""
        # Empty title
        response = client.post(
            "/api/projects", json={"title": ""}, headers=auth_headers
        )
        assert response.status_code == 422

        # Title too long
        response = client.post(
            "/api/projects", json={"title": "x" * 201}, headers=auth_headers
        )
        assert response.status_code == 422

    def test_color_validation(self, client: TestClient, auth_headers):
        """Test color format validation."""
        # Valid color
        response = client.post(
            "/api/projects",
            json={"title": "Test", "color": "#FF5733"},
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Invalid color
        response = client.post(
            "/api/projects",
            json={"title": "Test", "color": "red"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_tag_validation(self, client: TestClient, auth_headers):
        """Test tag validation."""
        # Tags are cleaned and deduplicated
        response = client.post(
            "/api/projects",
            json={
                "title": "Test",
                "tags": ["  Backend  ", "BACKEND", "frontend", "api"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        # Should be cleaned and deduplicated
        assert set(data["tags"]) == {"backend", "frontend", "api"}
