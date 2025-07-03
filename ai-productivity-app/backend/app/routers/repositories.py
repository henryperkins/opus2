"""Project-scoped repository endpoints.

Bridges the existing /api/import/git pipeline to a cleaner REST surface
under /api/projects/{project_id}/repositories.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, status

from app.dependencies import CurrentUserRequired, DatabaseDep
from app.models.import_job import ImportJob
from app.routers.import_git import start_import as _start_import_git

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/projects/{project_id}/repositories",
    tags=["repositories"],
)


def _extract(obj: dict, key: str, default=None):
    """Helper mirroring import_git._extract."""
    value = obj.get(key, default)
    if value is None:  # pragma: no cover – trivial
        raise HTTPException(status_code=422, detail=f"Missing field '{key}'")
    return value


# ---------------------------------------------------------------------------
# Attach repository (clone ➜ index ➜ embed)
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def connect_repository(  # noqa: WPS211 – param count acceptable
    project_id: int,
    payload: Annotated[dict, Body()],
    background_tasks: BackgroundTasks,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Kick off a git-import job for the given project."""
    repo_url = _extract(payload, "repo_url")
    branch = payload.get("branch", "main")

    # Re-use import_git.start_import to avoid duplicating business logic
    inner_payload = {
        "project_id": project_id,
        "repo_url": repo_url,
        "branch": branch,
    }
    return await _start_import_git(inner_payload, background_tasks, current_user, db)


# ---------------------------------------------------------------------------
# ImportJob status
# ---------------------------------------------------------------------------


@router.get("/{job_id}/status")
async def get_repository_status(
    project_id: int,
    job_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Return progress information for an ImportJob."""
    job: ImportJob | None = (
        db.query(ImportJob).filter_by(id=job_id, project_id=project_id).first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    return {
        "job_id": job.id,
        "project_id": job.project_id,
        "repo_url": job.repo_url,
        "branch": job.branch,
        "status": job.status,
        "progress_pct": job.progress_pct,
        "commit_sha": job.commit_sha,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
