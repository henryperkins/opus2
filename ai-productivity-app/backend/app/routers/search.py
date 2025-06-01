# Unified code/document search router (Phase-4)
# -------------------------------------------

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, select

from app.database import get_db
from sqlalchemy.orm import Session
from app.models.code import CodeEmbedding, CodeDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


###############################################################################
# Simple hybrid search (keyword only when no embeddings yet)                     
###############################################################################


def _keyword_search(db: Session, query: str, project_ids: list[int], limit: int) -> list[dict]:
    """Fallback keyword search directly against the SQL database."""
    stmt = (
        select(CodeEmbedding)
        .join(CodeDocument, CodeDocument.id == CodeEmbedding.document_id)
        .where(
            CodeDocument.project_id.in_(project_ids),
            or_(CodeEmbedding.chunk_content.ilike(f"%{query}%"), CodeEmbedding.symbol_name.ilike(f"%{query}%")),
        )
        .limit(limit)
    )

    rows = db.execute(stmt).scalars().all()
    results: list[dict] = []
    for r in rows:
        results.append(
            {
                "chunk_id": r.id,
                "content": r.chunk_content[:500],  # truncate for response
                "file_path": r.document.file_path if r.document else None,
                "language": r.document.language if r.document else None,
                "symbol": r.symbol_name,
                "search_type": "keyword",
            }
        )

    return results


###############################################################################
# Public endpoint                                                                
###############################################################################


@router.get("/")
async def search_code(  # noqa: D401
    query: str = Query(..., min_length=2, max_length=200),
    project_ids: Optional[List[int]] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return search results across code embeddings.

    At the moment only *keyword* search is implemented unless the vector-store
    backend has already indexed embeddings.  This provides a useful baseline
    while keeping the code entirely self-contained (no network calls).
    """

    # Default to *all* projects for now – in a real setup filter by ACLs
    if not project_ids:
        project_ids = [p.id for p in db.query(CodeDocument.project_id).distinct()] or [0]

    results = _keyword_search(db, query, project_ids, limit)

    return {"query": query, "results": results, "total": len(results)}
