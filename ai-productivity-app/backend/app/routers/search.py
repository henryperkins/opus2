# Unified code/document search router (Phase-4)
# -------------------------------------------

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, select

# NOTE: The original router only supported a very small *keyword* search.  We
# now transparently upgrade it to *hybrid* search by delegating to the shared
# :pyclass:`app.search.hybrid.HybridSearch` helper whenever embeddings and a
# compatible generator are available.  This keeps the public API fully
# backwards-compatible while providing significantly better relevance for
# indexed projects.

from app.database import get_db
from sqlalchemy.orm import Session
from app.models.code import CodeEmbedding, CodeDocument

# Optional – avoid hard dependency in minimal test environments
try:
    from app.embeddings.generator import EmbeddingGenerator  # noqa: F401
    from app.search.hybrid import HybridSearch  # noqa: F401

    _HAS_HYBRID = True
except Exception:  # pragma: no cover
    HybridSearch = None  # type: ignore
    EmbeddingGenerator = None  # type: ignore
    _HAS_HYBRID = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


# ---------------------------------------------------------------------------
# Autocomplete suggestions                                                    
# ---------------------------------------------------------------------------


@router.get("/suggestions")
async def search_suggestions(
    q: str = Query("", min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Return basic autocomplete suggestions for the *global search* bar.

    For now the implementation is intentionally *very* naive – matching file
    paths and symbol names that **contain** the typed substring.  The handler
    still proves useful when a proper vector based solution is not available
    and keeps the front-end UX consistent across environments.
    """

    if not q:
        return {"query": q, "suggestions": []}

    from app.models.code import CodeDocument, CodeEmbedding  # local import

    suggestions: list[str] = []

    # 1) Match file paths --------------------------------------------------
    doc_stmt = (
        select(CodeDocument.file_path)
        .where(CodeDocument.file_path.ilike(f"%{q}%"))
        .limit(limit)
    )
    suggestions.extend([row[0] for row in db.execute(doc_stmt).all()])

    # 2) Match symbol names -----------------------------------------------
    emb_stmt = (
        select(CodeEmbedding.symbol_name)
        .where(CodeEmbedding.symbol_name.is_not(None), CodeEmbedding.symbol_name.ilike(f"%{q}%"))
        .limit(limit)
    )
    suggestions.extend([row[0] for row in db.execute(emb_stmt).all()])

    # Unique + order by length (shorter first) for nicer UX
    uniq: list[str] = []
    for s in suggestions:
        if s and s not in uniq:
            uniq.append(s)

    uniq.sort(key=len)

    return {"query": q, "suggestions": uniq[:limit]}


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

    # ------------------------------------------------------------------
    # Prefer the new *HybridSearch* implementation if all dependencies are
    # available *and* at least one of the projects has already been indexed.
    # ------------------------------------------------------------------

    if _HAS_HYBRID:
        try:
            # Check quickly whether we have any vectors – if none exist we can
            # skip the heavy path straight away.
            has_vectors = (
                db.query(CodeEmbedding)
                .join(CodeDocument, CodeDocument.id == CodeEmbedding.document_id)
                .filter(CodeDocument.project_id.in_(project_ids), CodeEmbedding.embedding.is_not(None))
                .limit(1)
                .first()
                is not None
            )

            if has_vectors:
                generator = EmbeddingGenerator() if EmbeddingGenerator else None
                hybrid = HybridSearch(db, embedding_generator=generator)
                results = await hybrid.search(query, project_ids=project_ids, limit=limit)
                return {"query": query, "results": results, "total": len(results)}
        except Exception as exc:  # pragma: no cover – fallback silently
            logger.warning("Hybrid search failed, falling back to keyword-only: %s", exc)

    # Fallback: pure keyword search
    results = _keyword_search(db, query, project_ids, limit)

    return {"query": query, "results": results, "total": len(results)}
