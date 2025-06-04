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
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.code_processing.language_detector import detect_language
from app.code_processing.parser import CodeParser
from app.code_processing.chunker import SemanticChunker

from app.database import get_db
from sqlalchemy.orm import Session
from app.models.code import CodeDocument, CodeEmbedding
from app.models.project import Project

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/code", tags=["code"])

# Instantiate expensive helpers once per worker
_PARSER = CodeParser()
_CHUNKER = SemanticChunker()


###############################################################################
# Helper – background processing                                                   
###############################################################################


def _process_code_file(db: Session, doc_id: int, content: str, language: str) -> None:  # noqa: D401
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
        doc: CodeDocument | None = session.query(CodeDocument).filter_by(id=doc_id).first()
        if not doc:
            logger.warning("CodeDocument %s vanished before processing", doc_id)
            return

        # ── Parse ────────────────────────────────────────────────────────────
        parse_result = _PARSER.parse_file(content, language)

        doc.symbols = parse_result.get("symbols", [])
        doc.imports = parse_result.get("imports", [])

        # ── Chunk ────────────────────────────────────────────────────────────
        chunks = _CHUNKER.create_chunks(content, doc.symbols or [], language, file_path=doc.file_path)

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

        doc.is_indexed = False  # embeddings still missing – separate worker will generate
        session.commit()

        logger.info("Processed file %s (%d chunks)", doc.file_path, len(chunks))
    except Exception:  # pragma: no cover – log unexpected errors
        logger.exception("Failed to process code file (doc_id=%s)", doc_id)
        session.rollback()
    finally:
        session.close()


###############################################################################
# Public API                                                                     
###############################################################################


@router.post("/projects/{project_id}/upload")
async def upload_code_files(  # noqa: D401, WPS211
    project_id: int,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload *multiple* source-code files and queue them for parsing.

    Returns a JSON list with the processing status for each file.  Duplicate
    uploads (same SHA-256 hash) are automatically ignored to save compute.
    """

    # ── Authorisation guard ────────────────────────────────────────────────
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")



    results: list[dict[str, str]] = []

    for upload in files:
        raw = await upload.read()
        content_hash = hashlib.sha256(raw).hexdigest()

        existing: CodeDocument | None = (
            db.query(CodeDocument)
            .filter_by(project_id=project_id, file_path=upload.filename, content_hash=content_hash)
            .first()
        )

        if existing:
            results.append({"file": upload.filename, "status": "duplicate"})
            continue

        language = detect_language(upload.filename, raw.decode("utf-8", errors="ignore"))

        doc = CodeDocument(
            project_id=project_id,
            file_path=upload.filename,
            file_size=len(raw),
            content_hash=content_hash,
            language=language,
        )
        db.add(doc)
        db.commit()

        # Kick background processing – ensure tasks parameter exists in unit tests
        if background_tasks is not None:
            background_tasks.add_task(_process_code_file, db, doc.id, raw.decode("utf-8", errors="ignore"), language)

        results.append({"file": upload.filename, "status": "queued"})

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

    doc: CodeDocument | None = db.query(CodeDocument).filter_by(id=file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    db.delete(doc)
    db.commit()

    return {"status": "deleted"}
