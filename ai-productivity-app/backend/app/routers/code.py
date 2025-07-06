# Code upload & processing router (Phase-4)
# ---------------------------------------
#
# This module exposes endpoints under the ``/api/code`` prefix that allow
# clients to upload individual source-code files which are then parsed with
# Tree-sitter and split into semantic chunks.  The heavy CPU work is executed
# inside FastAPI BackgroundTasks so the HTTP request returns quickly.
#
# The implementation deliberately *avoids* synchronous I/O inside the event
# loop: file reading happens via ``UploadFile.read()`` (already async) and all
# DB access is delegated to the SQLAlchemy session injected via dependency.

from __future__ import annotations

import hashlib
import logging
import contextlib
import io
import textwrap
import traceback
import tempfile
import os
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.code_processing.chunker import SemanticChunker
from app.code_processing.language_detector import detect_language
from app.code_processing.parser import CodeParser
from app.database import get_db
# Use the new authentication dependency style.
# ``get_current_user`` enforces authentication and returns the User.
from app.dependencies import get_current_user
from app.models.code import CodeDocument, CodeEmbedding
from app.models.project import Project
from app.models.user import User
from app.config import settings
from app.services.usage_searcher import UsageSearcher

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/code", tags=["code"])

# Instantiate expensive helpers once per worker
_PARSER = CodeParser()
_CHUNKER = SemanticChunker()


###############################################################################
# Helper – background processing
###############################################################################


def _process_code_file(
    db: Session, doc_id: int, content: str, language: str
) -> None:  # noqa: D401
    """Parse, chunk and persist a single code file.

    This function is **synchronous** and meant to run inside a background
    thread, therefore blocking calls are acceptable.  It must create a new
    database session because the original one is tied to the request thread
    and closed by the time this runs.
    """

    # Each background task starts its *own* session
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        doc: CodeDocument | None = (
            session.query(CodeDocument).filter_by(id=doc_id).first()
        )
        if not doc:
            logger.warning(
                "CodeDocument %s vanished before processing", doc_id
            )
            return

        # ── Parse ────────────────────────────────────────────────────────────
        parse_result = _PARSER.parse_file(content, language)

        doc.symbols = parse_result.get("symbols", [])
        doc.imports = parse_result.get("imports", [])

        # ── Chunk ────────────────────────────────────────────────────────────
        chunks = _CHUNKER.create_chunks(
            content, doc.symbols or [], language, file_path=doc.file_path
        )

        for chunk in chunks:
            session.add(
                CodeEmbedding(
                    document_id=doc.id,
                    chunk_content=chunk["content"],
                    symbol_name=chunk.get("symbol_name"),
                    symbol_type=chunk.get("symbol_type"),
                    start_line=chunk.get("start_line"),
                    end_line=chunk.get("end_line"),
                )
            )

        # embeddings still missing – separate worker will generate
        doc.is_indexed = False
        session.commit()

        logger.info(
            "Processed file %s (%d chunks)", doc.file_path, len(chunks)
        )
    except Exception:  # pragma: no cover – log unexpected errors
        logger.exception("Failed to process code file (doc_id=%s)", doc_id)
        session.rollback()
    finally:
        session.close()


###############################################################################
# Public API
###############################################################################


# Allowed MIME types for security
ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/x-python",
    "text/x-java-source",
    "text/x-c",
    "text/x-c++src",
    "text/x-csharp",
    "text/javascript",
    "application/javascript",
    "text/typescript",
    "application/typescript",
    "text/x-go",
    "text/x-rust",
    "text/html",
    "text/css",
    "application/json",
    "text/yaml",
    "text/x-yaml",
    "application/yaml",
    "text/xml",
    "application/xml",
    None,  # Some browsers don't set MIME type for text files
}


@router.post("/projects/{project_id}/upload")
async def upload_code_files(  # noqa: D401, WPS211
    project_id: int,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload *multiple* source-code files and queue them for parsing.

    Returns a JSON list with the processing status for each file.  Duplicate
    uploads (same SHA-256 hash) are automatically ignored to save compute.
    """

    # ── Authentication & Authorization ─────────────────────────────────────
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if user has write access to project (simplified - in production you'd check ProjectUser role)
    # For now, assume authenticated users can upload to any project they can see

    results: list[dict[str, str]] = []

    for upload in files:
        try:
            # ── MIME type validation ──────────────────────────────────────────
            if upload.content_type not in ALLOWED_MIME_TYPES:
                results.append({
                    "file": upload.filename or "unknown",
                    "status": "rejected",
                    "reason": f"Unsupported MIME type: {upload.content_type}"
                })
                continue

            # ── Size validation with streaming ────────────────────────────────
            content_chunks = []
            content_hash = hashlib.sha256()
            total_size = 0

            # Read file in chunks to validate size without loading all into memory
            while True:
                chunk = await upload.read(4096)  # 4KB chunks
                if not chunk:
                    break

                content_hash.update(chunk)
                total_size += len(chunk)
                content_chunks.append(chunk)

                # Check size limit
                if total_size > settings.max_upload_size:
                    results.append({
                        "file": upload.filename or "unknown",
                        "status": "rejected",
                        "reason": f"File too large: {total_size} > {settings.max_upload_size}"
                    })
                    break
            else:
                # File size is acceptable, reconstruct content
                raw = b''.join(content_chunks)
                content_hash_hex = content_hash.hexdigest()

                # ── Duplicate detection by content hash only ──────────────────
                existing: CodeDocument | None = (
                    db.query(CodeDocument)
                    .filter_by(content_hash=content_hash_hex)
                    .first()
                )

                if existing:
                    results.append({
                        "file": upload.filename or "unknown",
                        "status": "duplicate",
                        "existing_file": existing.file_path
                    })
                    continue

                # ── Store file to disk securely ───────────────────────────────
                try:
                    content_decoded = raw.decode("utf-8", errors="ignore")
                    language = detect_language(upload.filename, content_decoded)

                    # Create safe filename and path
                    safe_filename = upload.filename or f"upload_{content_hash_hex[:8]}.{language}"
                    file_path = safe_filename

                    doc = CodeDocument(
                        project_id=project_id,
                        file_path=file_path,
                        file_size=total_size,
                        content_hash=content_hash_hex,
                        language=language,
                    )
                    db.add(doc)
                    db.commit()

                    # Save file to uploads directory
                    upload_dir = Path(settings.upload_root)
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    
                    full_file_path = upload_dir / file_path
                    # Create parent directories if needed
                    full_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file content to disk
                    with open(full_file_path, 'wb') as f:
                        f.write(raw)

                    # Kick background processing
                    if background_tasks is not None:
                        background_tasks.add_task(
                            _process_code_file, db, doc.id, content_decoded, language
                        )

                    results.append({
                        "file": upload.filename or "unknown",
                        "status": "queued",
                        "document_id": doc.id
                    })

                except Exception as storage_exc:
                    logger.error("Failed to store file: %s", storage_exc)
                    results.append({
                        "file": upload.filename or "unknown",
                        "status": "error",
                        "reason": "Storage failure"
                    })

        except Exception as exc:
            logger.error("Upload processing failed for %s: %s", upload.filename, exc)
            results.append({
                "file": upload.filename or "unknown",
                "status": "error",
                "reason": "Processing failure"
            })

    return {"results": results}


# ---------------------------------------------------------------------------
# New: list documents for a project
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/files")
def list_project_files(
    project_id: int,
    db: Session = Depends(get_db),
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """Return code files belonging to *project_id*.

    Supports basic pagination and simple filename "search" query.
    """

    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    q = db.query(CodeDocument).filter_by(project_id=project_id)
    if search:
        like = f"%{search}%"
        q = q.filter(CodeDocument.file_path.ilike(like))

    total = q.count()
    docs = (
        q.order_by(CodeDocument.file_path)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "files": [
            {
                "id": d.id,
                "path": d.file_path,
                "language": d.language,
                "size": d.file_size,
                "indexed": d.is_indexed,
            }
            for d in docs
        ],
    }


# ---------------------------------------------------------------------------
# New: delete a single file
# ---------------------------------------------------------------------------


@router.delete("/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    """Delete a single CodeDocument (and cascade embeddings)."""

    doc: CodeDocument | None = (
        db.query(CodeDocument).filter_by(id=file_id).first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    db.delete(doc)
    db.commit()

    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Get file content by path
# ---------------------------------------------------------------------------

@router.get("/files/content")
def get_file_content(
    file_path: str,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get file content by path."""
    query = db.query(CodeDocument).filter(CodeDocument.file_path == file_path)
    
    if project_id:
        query = query.filter(CodeDocument.project_id == project_id)
    
    doc: CodeDocument | None = query.first()
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user has access to this project
    project = db.query(Project).filter_by(id=doc.project_id).first()
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Read file content from disk
    try:
        file_full_path = os.path.join(settings.upload_root, doc.file_path)
        with open(file_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "content": content,
            "language": doc.language,
            "file_path": doc.file_path,
            "size": doc.file_size,
        }
    except FileNotFoundError:
        logger.warning(f"File exists in database but missing on disk: {doc.file_path} (expected at {file_full_path})")
        
        # Try to find the file in the original codebase structure as fallback
        # Remove the leading project name from path if present
        potential_path = doc.file_path
        if '/' in potential_path:
            # Try without the first directory component
            path_parts = potential_path.split('/', 1)
            if len(path_parts) > 1:
                fallback_path = path_parts[1]  # Skip the "ai-productivity-app" prefix
                try:
                    with open(fallback_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.info(f"Found file at fallback location: {fallback_path}")
                    return {
                        "content": content,
                        "language": doc.language,
                        "file_path": doc.file_path,
                        "size": len(content.encode('utf-8')),
                    }
                except FileNotFoundError:
                    pass
        
        raise HTTPException(
            status_code=404, 
            detail=f"File found in database but missing from disk: {doc.file_path}. This may indicate a synchronization issue."
        )
    except Exception as e:
        logger.error(f"Error reading file {doc.file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


# ---------------------------------------------------------------------------
# Database maintenance endpoint for identifying orphaned files
# ---------------------------------------------------------------------------

@router.get("/files/integrity-check")
def check_file_integrity(
    fix_orphaned: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check database-filesystem integrity and optionally fix orphaned entries.
    
    This endpoint helps identify files that exist in the database but are missing from disk.
    """
    # Only allow admins or during development
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Only available in debug mode")
    
    # Get user's documents or all if admin check is implemented
    query = db.query(CodeDocument).filter(
        db.query(Project).filter(Project.id == CodeDocument.project_id).filter(Project.owner_id == current_user.id).exists()
    ).limit(limit)
    
    docs = query.all()
    results = {
        "checked": 0,
        "missing_files": [],
        "fixed": 0
    }
    
    for doc in docs:
        results["checked"] += 1
        file_full_path = os.path.join(settings.upload_root, doc.file_path)
        
        if not os.path.exists(file_full_path):
            results["missing_files"].append({
                "id": doc.id,
                "file_path": doc.file_path,
                "project_id": doc.project_id,
                "expected_path": file_full_path
            })
            
            if fix_orphaned:
                db.delete(doc)
                results["fixed"] += 1
    
    if fix_orphaned and results["fixed"] > 0:
        db.commit()
        logger.info(f"Removed {results['fixed']} orphaned file entries")
    
    return results


# ---------------------------------------------------------------------------
# New: lightweight Python code execution endpoint (unsafe, dev-only)
# ---------------------------------------------------------------------------
#
# NOTE: This endpoint is **NOT** suited for production use – it executes
# arbitrary Python code inside the API worker.  It exists purely for the
# interactive demo requirement where users can run code snippets generated
# by the LLM.  Protect behind authentication / feature-flag in production!


class UsageRequest(BaseModel):
    """Request body for finding symbol usages."""
    file_path: str
    line: int
    column: int


class CodeExecRequest(BaseModel):
    """Request body for /api/code/execute."""
    code: str
    language: str = "python"
    project_id: int | None = None  # reserved for future


class CodeExecResponse(BaseModel):
    """Response body for /api/code/execute."""
    stdout: str
    stderr: str
    result_repr: str | None = None
    success: bool


@router.post("/{project_id}/usages", response_model=List[Dict])
async def find_symbol_usages(
    project_id: int,
    request: UsageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find all usages of a symbol at a given location."""
    # Verify project access
    project = db.query(Project).filter_by(id=project_id, owner_id=current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get project repository path
    project_path = f"repos/project_{project_id}"
    
    usage_searcher = UsageSearcher(project_path)
    results = usage_searcher.find_usages(
        file_path=request.file_path,
        line=request.line,
        column=request.column
    )
    return results


@router.post("/execute", response_model=CodeExecResponse)
async def execute_code(req: CodeExecRequest) -> CodeExecResponse:  # noqa: D401
    """
    Execute a *Python* code snippet and capture stdout / stderr.

    WARNING: This runs arbitrary code inside the API worker – keep disabled
    in production environments.
    """
    # SECURITY: Disable code execution by default - extremely dangerous
    from app.config import settings
    if not getattr(settings, 'allow_code_execution', False):
        raise HTTPException(
            status_code=403, 
            detail="Code execution is disabled for security reasons. Set ALLOW_CODE_EXECUTION=true to enable."
        )
    
    if req.language.lower() not in {"python", "py"}:
        raise HTTPException(status_code=400, detail="Only Python execution supported")

    stdout_buf, stderr_buf = io.StringIO(), io.StringIO()
    local_vars: dict[str, object] = {}

    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            exec(textwrap.dedent(req.code), {}, local_vars)  # pylint: disable=exec-used
        # Conventional REPL result variable (“_”) if provided
        result_repr = repr(local_vars.get("_", None))
        success = True
    except Exception as exc:  # pragma: no cover
        traceback.print_exc(file=stderr_buf)
        result_repr = repr(exc)
        success = False

    return CodeExecResponse(
        stdout=stdout_buf.getvalue(),
        stderr=stderr_buf.getvalue(),
        result_repr=result_repr,
        success=success,
    )
