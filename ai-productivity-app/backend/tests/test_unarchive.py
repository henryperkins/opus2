"""Tests for project unarchive endpoint."""

from fastapi.testclient import TestClient

from app.models.project import Project, ProjectStatus
from app.models.timeline import TimelineEvent
from app.models.user import User


def _create_user(db):
    user = User(username="alice", email="alice@example.com", password_hash="hashed")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_archived_project(db, owner_id):
    project = Project(title="Old", status=ProjectStatus.ARCHIVED, owner_id=owner_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_unarchive_endpoint(client: TestClient, db):
    """POST /projects/{id}/unarchive should reactivate project and log an event."""

    user = _create_user(db)
    project = _create_archived_project(db, user.id)

    headers = {"Authorization": "Bearer stub"}

    resp = client.post(f"/api/projects/{project.id}/unarchive", headers=headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "active"

    # Timeline event created
    events = (
        db.query(TimelineEvent).filter(TimelineEvent.project_id == project.id).all()
    )
    assert any(e.title == "Project unarchived" for e in events)
