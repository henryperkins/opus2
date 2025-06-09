"""Unit tests for Git import API."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.fixture()
def mock_clone(monkeypatch):
    """Patch GitManager.clone_repository to avoid real network access."""

    async def _fake_clone(repo_url: str, project_id: int, branch: str = "main"):
        return {
            "repo_path": "/tmp/fake",
            "repo_name": "fake-repo",
            "commit_sha": "deadbeef",
            "branch": branch,
            "files": [
                {"path": "main.py", "size": 10, "modified": 0, "sha": "1"},
            ],
            "total_files": 1,
        }

    from app.routers import import_git as import_router

    monkeypatch.setattr(import_router._GIT_MANAGER, "clone_repository", _fake_clone)


def test_import_job_creation(db, mock_clone):
    """POST /api/import/git returns 202 and creates DB row."""

    # create user & project
    from app.models.user import User
    from app.models.project import Project

    user = User(username="u", email="u@x", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    project = Project(title="P", owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    # Auth header stub
    headers = {"Authorization": "Bearer token"}

    resp = client.post(
        "/api/import/git",
        json={"project_id": project.id, "repo_url": "https://example.com/r.git"},
        headers=headers,
    )

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    from app.models.import_job import ImportJob

    job = db.query(ImportJob).filter_by(id=job_id).first()
    assert job is not None
    assert job.status.name == "QUEUED"

    # Run background coroutine synchronously so we can assert completed state
# Execute async job synchronously for test
    asyncio.run(import_router._run_import_job(job_id))

    db.refresh(job)
    assert job.status.name == "COMPLETED"
