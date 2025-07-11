"""Repository import endpoints."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    status,
    Header,
)

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


def _validate_repo_url(url: str) -> None:
    """Security: Sanity-check git URL to prevent command injection / local file access."""

    allowed_protocols = ("https://", "ssh://git@")
    if not url.startswith(allowed_protocols):
        raise HTTPException(
            status_code=400,
            detail="Invalid repository URL. Must start with 'https://' or 'ssh://git@'.",
        )

    # Strict character whitelist to prevent command injection via url
    if not re.fullmatch(r"[a-zA-Z0-9@:/._\-]+", url):
        raise HTTPException(
            status_code=400,
            detail="Invalid repository URL. Contains unsafe characters.",
        )


###############################################################################
# Validation endpoint (quick HEAD clone)
###############################################################################


@router.post("/validate")
async def validate_repo(
    payload: Annotated[dict, Body()],
    x_git_token: Annotated[str | None, Header()] = None,
):
    """Light-weight clone to verify URL / auth without creating ImportJob."""

    repo_url = _extract(payload, "repo_url")
    _validate_repo_url(repo_url)
    branch = payload.get("branch", "main")

    try:
        info = await _GIT_MANAGER.clone_repository(
            repo_url, project_id=0, branch=branch, token=x_git_token
        )  # tmp path
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
# Repository status endpoint
###############################################################################


@router.get("/repository/{project_id}")
async def get_repository_status(
    project_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Get repository connection status and stats for a project."""

    # Verify project access
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Access denied: You don't own this project"
        )

    # Get latest import job for this project
    latest_job = (
        db.query(ImportJob)
        .filter_by(project_id=project_id)
        .order_by(ImportJob.created_at.desc())
        .first()
    )

    if not latest_job:
        return {
            "connected": False,
            "status": "not_connected",
            "repo_info": None,
            "stats": {"total_files": 0, "documents_added": 0},
        }

    # Get document count for this project
    from app.models.code import CodeDocument

    document_count = db.query(CodeDocument).filter_by(project_id=project_id).count()

    return {
        "connected": latest_job.status == ImportStatus.COMPLETED,
        "status": latest_job.status.value,
        "repo_info": {
            "repo_url": latest_job.repo_url,
            "branch": latest_job.branch,
            "commit_sha": latest_job.commit_sha,
            "last_sync": (
                latest_job.updated_at.isoformat() if latest_job.updated_at else None
            ),
        },
        "stats": {"total_files": document_count, "documents_added": document_count},
        "progress": {
            "phase": latest_job.status.value,
            "percent": latest_job.progress_pct,
        },
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
    _validate_repo_url(repo_url)
    branch = payload.get("branch", "main")
    include_patterns = payload.get("include_patterns", [])
    exclude_patterns = payload.get("exclude_patterns", [])

    # Authorisation - verify project exists and user owns it
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Access denied: You don't own this project"
        )

    # Create job
    job = ImportJob(
        project_id=project_id,
        requested_by=current_user.id,
        repo_url=repo_url,
        branch=branch,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
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

        async def _notify(**kwargs):  # helper coroutine for typed notifications
            """Send WebSocket notification using tracked task manager.

            Leveraging ``notify_manager.send_async`` ensures that every
            background send is **registered** with the per-user task registry
            so it can be cancelled automatically when the client disconnects
            (Hardening Checklist item 2-C).
            """

            await notify_manager.send_async(
                user_id,
                {"type": "import", "job_id": job_id, **kwargs},
            )

        # ------------------------------------------------------------------
        # 1. Clone repository
        # ------------------------------------------------------------------
        job.status = ImportStatus.CLONING
        job.progress_pct = 0
        db.commit()
        await _notify(phase="cloning", percent=0)

        try:
            clone_info = await _GIT_MANAGER.clone_repository(
                job.repo_url,
                project_id=job.project_id,
                branch=job.branch,
                include_patterns=job.include_patterns,
                exclude_patterns=job.exclude_patterns,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Clone failed")
            job.status = ImportStatus.FAILED
            job.error = str(exc)
            db.commit()
            await _notify(phase="failed", message=str(exc))
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
        from app.routers.code import _process_code_file  # re-use existing helper

        # Import here to avoid circular issues at top of module
        from app.database.transactions import atomic  # local import inside fn

        tasks = []
        with atomic(db):
            for idx, file_meta in enumerate(files):
                file_path = file_meta["path"]
                full_path = clone_info["repo_path"] + "/" + file_path

                try:
                    # Reading file content is blocking, move to thread
                    content = await asyncio.to_thread(_read_file_content, full_path)
                    if content is None:
                        continue
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Skip file %s: %s", file_path, exc)
                    continue

                doc = CodeDocument(
                    project_id=job.project_id,
                    commit_sha=job.commit_sha,  # Propagate commit SHA
                    file_path=file_path,
                    file_size=file_meta.get("size", 0),
                    content_hash=file_meta.get("sha", ""),
                    language=detect_language(file_path, content),
                    is_indexed=True,  # Mark as indexed by parser
                )
                db.add(doc)
                db.flush()  # ensure PK assigned so background task can query

                task = asyncio.create_task(
                    asyncio.to_thread(
                        _process_code_file, db, doc.id, content, doc.language
                    )
                )
                tasks.append(task)

                # Update progress in memory
                pct = 10 + int(((idx + 1) / total) * 60)
                if pct > job.progress_pct:
                    job.progress_pct = pct
                    job.touch()
                    await _notify(phase="indexing", percent=job.progress_pct)

        # Await all parsing tasks ------------------------------------------------
        try:
            await asyncio.gather(*tasks)
        except Exception as exc:
            logger.exception("Code processing task failed")
            job.status = ImportStatus.FAILED
            job.error = f"Code processing error: {exc}"
            db.commit()
            await _notify(phase="failed", message=job.error)
            return

        # ------------------------------------------------------------------
        # 3. Wait until embedding finished (simplified – check flag)
        # ------------------------------------------------------------------
        job.status = ImportStatus.EMBEDDING
        job.progress_pct = 80
        db.commit()
        await _notify(phase="embedding", percent=80)

        # Poll until all documents are indexed (is_indexed=True) – give up after 10 min
        import time

        deadline = time.time() + 600
        while time.time() < deadline:
            # Get remaining unembedded documents
            remaining = await asyncio.to_thread(
                lambda: db.query(CodeDocument)
                .filter_by(project_id=job.project_id, is_indexed=False)
                .count()
            )

            processed = total - remaining if total else 0
            pct = 80 + int((processed / total) * 20) if total else 99

            if pct > job.progress_pct:
                job.progress_pct = pct
                job.touch()
                db.commit()
                await _notify(phase="embedding", percent=pct)

            if remaining == 0:
                break

            await asyncio.sleep(5)

        # ------------------------------------------------------------------
        # 4. Completed
        # ------------------------------------------------------------------
        job.status = ImportStatus.COMPLETED
        job.progress_pct = 100
        db.commit()
        await _notify(phase="completed", percent=100)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Import job crashed")
        if job:
            job.status = ImportStatus.FAILED
            job.error = str(exc)
            db.commit()
            await _notify(phase="failed", message=str(exc))
    finally:
        db.close()


def _read_file_content(path: str) -> str | None:
    """Read file content with error handling."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fp:
            return fp.read()
    except Exception as exc:
        logger.warning("Could not read file %s: %s", path, exc)
        return None
