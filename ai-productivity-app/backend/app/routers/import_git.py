"""Repository import endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status

from app.dependencies import CurrentUserRequired, DatabaseDep
from app.models.import_job import ImportJob, ImportStatus
from app.models.project import Project
from app.code_processing.git_integration import GitManager
from app.websocket.notify_manager import notify_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import/git", tags=["git-import"])

# Singleton GitManager – clone path under ./data/git (ensures persistence)
_GIT_MANAGER = GitManager(base_path="data/git")


# ---------------------------------------------------------------------------
# Payload schemas (lightweight, avoid Pydantic for test-time perf)
# ---------------------------------------------------------------------------


def _extract(obj: dict, key: str, default=None):
    v = obj.get(key, default)
    if v is None:
        raise HTTPException(status_code=422, detail=f"Missing field '{key}'")
    return v


###############################################################################
# Validation endpoint (quick HEAD clone)
###############################################################################


@router.post("/validate")
async def validate_repo(
    payload: Annotated[dict, Body()],
):
    """Light-weight clone to verify URL / auth without creating ImportJob."""

    repo_url = _extract(payload, "repo_url")
    branch = payload.get("branch", "main")

    try:
        info = await _GIT_MANAGER.clone_repository(repo_url, project_id=0, branch=branch)  # tmp path
    except Exception as exc:  # noqa: BLE001
        logger.warning("validate_repo failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    # Remove files list for brevity
    return {
        "repo_name": info["repo_name"],
        "commit_sha": info["commit_sha"],
        "total_files": info["total_files"],
    }


###############################################################################
# Import – async background job
###############################################################################


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_import(
    payload: Annotated[dict, Body()],
    background_tasks: BackgroundTasks,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):  # noqa: WPS211 – acceptable param count
    """Create job and spawn background task."""

    project_id = int(_extract(payload, "project_id"))
    repo_url = _extract(payload, "repo_url")
    branch = payload.get("branch", "main")

    # Authorisation
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create job
    job = ImportJob(
        project_id=project_id,
        requested_by=current_user.id,
        repo_url=repo_url,
        branch=branch,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Kick background task
    background_tasks.add_task(_run_import_job, job.id)

    return {"job_id": job.id}


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


async def _run_import_job(job_id: int) -> None:  # noqa: D401, WPS231, WPS210
    from app.database import SessionLocal  # local import to avoid circular
    from app.models.code import CodeDocument

    db = SessionLocal()
    try:
        job: ImportJob | None = db.query(ImportJob).filter_by(id=job_id).first()
        if not job:
            logger.error("Import job %s vanished", job_id)
            return

        user_id = job.requested_by or 0

        def _notify(**kwargs):  # helper closure
            asyncio.create_task(notify_manager.send(user_id, {"type": "import", "job_id": job_id, **kwargs}))

        # ------------------------------------------------------------------
        # 1. Clone repository
        # ------------------------------------------------------------------
        job.status = ImportStatus.CLONING
        job.progress_pct = 0
        db.commit()
        _notify(phase="cloning", percent=0)

        try:
            clone_info = await _GIT_MANAGER.clone_repository(job.repo_url, project_id=job.project_id, branch=job.branch)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Clone failed")
            job.status = ImportStatus.FAILED
            job.error = str(exc)
            db.commit()
            _notify(phase="failed", message=str(exc))
            return

        job.commit_sha = clone_info["commit_sha"]

        # ------------------------------------------------------------------
        # 2. Insert CodeDocument rows + queue background parse
        # ------------------------------------------------------------------
        job.status = ImportStatus.INDEXING
        db.commit()
        total = clone_info["total_files"] or 1
        files = clone_info["files"]

        from app.code_processing.language_detector import detect_language
        from app.models.code import CodeDocument  # noqa: WPS433
        from app.routers.code import _process_code_file  # re-use existing helper

        for idx, file_meta in enumerate(files):
            file_path = file_meta["path"]
            full_path = clone_info["repo_path"] + "/" + file_path
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skip file %s: %s", file_path, exc)
                continue

            doc = CodeDocument(
                project_id=job.project_id,
                file_path=file_path,
                file_size=file_meta.get("size", 0),
                content_hash=file_meta.get("sha", ""),
                language=detect_language(file_path, content),
            )
            db.add(doc)
            db.commit()

            # Queue background parse
            asyncio.create_task(_process_code_file(db, doc.id, content, doc.language))

            pct = 10 + int((idx / total) * 60)
            if pct > job.progress_pct:
                job.progress_pct = pct
                job.touch()
                db.commit()
                _notify(phase="indexing", percent=job.progress_pct)

        # ------------------------------------------------------------------
        # 3. Wait until embedding finished (simplified – check flag)
        # ------------------------------------------------------------------
        job.status = ImportStatus.EMBEDDING
        db.commit()
        _notify(phase="embedding", percent=80)

        # Poll until all documents are indexed (is_indexed=True) – give up after 10 min
        import time

        deadline = time.time() + 600
        while time.time() < deadline:
            remaining = db.query(CodeDocument).filter_by(project_id=job.project_id, is_indexed=False).count()
            if remaining == 0:
                break
            await asyncio.sleep(5)

        # ------------------------------------------------------------------
        # 4. Completed
        # ------------------------------------------------------------------
        job.status = ImportStatus.COMPLETED
        job.progress_pct = 100
        db.commit()
        _notify(phase="completed", percent=100)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Import job crashed")
        if job:
            job.status = ImportStatus.FAILED
            job.error = str(exc)
            db.commit()
            _notify(phase="failed", message=str(exc))
    finally:
        db.close()
