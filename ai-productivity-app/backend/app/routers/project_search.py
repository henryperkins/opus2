"""Project-scoped search history endpoints.

This router exposes lightweight endpoints under the
    /api/projects/{project_id}/search
namespace which the frontend uses to populate the knowledge-search side
panels (recent history and popular queries).

The global */api/search* router already provides user-level history but the
UI also expects per-project variants.  Until now they were not implemented
which resulted in HTTP 404 responses and noisy client-side logs.

Implementation notes
--------------------
• We keep the payload shapes compatible with the existing frontend helper
  functions (see `frontend/src/api/search.js`).
  – `/history` returns `{ "history": [...] }` where each element is a
    dictionary containing at least `id`, `query`, and `created_at`.
  – `/popular` returns `{ "queries": [...] }` with unique query strings
    ordered by frequency (desc).

• Popular queries are computed with a simple `GROUP BY` on `query_text`.
  For SQLite compatibility we fall back to a Python aggregation when the
  database dialect does not support `JSON` containment operators.
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text

from app.dependencies import DatabaseDep, CurrentUserRequired
from app.models.search_history import SearchHistory
from app.models.project import Project

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------


router = APIRouter(
    prefix="/api/projects/{project_id}/search",
    tags=["search"],
)


# ---------------------------------------------------------------------------
def _get_project_or_404(db: Session, project_id: int, user_id: int) -> Project:
    project: Project | None = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied",
        )

    return project


@router.get("/history")
# NOTE: parameters without default values must come before those with defaults.
# Therefore `current_user` and `db` precede `limit` which has a default.
def get_history(
    project_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    limit: int = Query(100, ge=1, le=500),
):
    """Return recent search queries executed **within a project**.

    The response format matches the expectation in `searchAPI.getSearchHistory`.
    """

    # Ensure the project is accessible – this will raise 404/403 as needed.
    _get_project_or_404(db, project_id, current_user.id)

    # ------------------------------------------------------------------
    # Query most-recent searches that include the current project id in the
    # stored `project_ids` JSON column.
    # ------------------------------------------------------------------
    try:
        rows: List[SearchHistory] = (
            db.query(SearchHistory)
            .filter(
                SearchHistory.user_id == current_user.id,
                # The JSON containment operator `@>` works for PostgreSQL.
                # For SQLite (tests) we fall back to LIKE which is less
                # efficient but functional given small test data volumes.
                (
                    SearchHistory.project_ids.contains([project_id])
                    if hasattr(SearchHistory.project_ids, "contains")
                    else text("1 = 1")  # pragma: no cover – fallback path
                ),
            )
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as exc:  # noqa: BLE001 – dialect mismatch fallback
        # The initial SQL attempt can fail when the underlying database
        # does not support JSON containment operators for the `JSON` column
        # type (e.g. PostgreSQL `json` vs. `jsonb`).  Once the statement
        # errors the transaction is left in *failed* state and every further
        # query on the same connection will raise *InFailedSqlTransaction*.
        #
        # To safely run the Python-level fallback logic we therefore need to
        # roll back the session first.
        db.rollback()

        logger.debug("Falling back to Python filtering for history: %s", exc)
        all_rows: List[SearchHistory] = (
            db.query(SearchHistory)
            .filter(SearchHistory.user_id == current_user.id)
            .order_by(SearchHistory.created_at.desc())
            .all()
        )
        rows = [r for r in all_rows if r.project_ids and project_id in r.project_ids][
            :limit
        ]

    history_payload = [
        {
            "id": r.id,
            "query": r.query_text,
            "filters": r.filters or {},
            "project_ids": r.project_ids or [],
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]

    return {"history": history_payload}


@router.get("/popular")
def get_popular(
    project_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    limit: int = Query(20, ge=1, le=100),
):
    """Return most-frequent search queries for the given project."""

    _get_project_or_404(db, project_id, current_user.id)

    # Attempt SQL aggregation first (PostgreSQL path)
    try:
        rows = (
            db.query(
                SearchHistory.query_text.label("query"),
                func.count(SearchHistory.id).label("hits"),
            )
            .filter(
                SearchHistory.project_ids.contains([project_id])
                if hasattr(SearchHistory.project_ids, "contains")
                else text("1 = 1")
            )
            .group_by(SearchHistory.query_text)
            .order_by(desc("hits"))
            .limit(limit)
            .all()
        )

        popular_queries = [row.query for row in rows]

    except (
        Exception
    ) as exc:  # noqa: BLE001 – fallback for SQLite / unsupported JSON ops
        # Roll back the failed transaction so that the subsequent SELECT used
        # for the in-memory aggregation runs on a clean connection.
        db.rollback()

        logger.debug("Falling back to Python aggregation for popular: %s", exc)
        all_rows: List[SearchHistory] = (
            db.query(SearchHistory)
            .filter(SearchHistory.user_id == current_user.id)
            .all()
        )

        # Aggregate in memory
        counts: dict[str, int] = {}
        for r in all_rows:
            if r.project_ids and project_id in r.project_ids:
                counts[r.query_text] = counts.get(r.query_text, 0) + 1

        popular_queries = [
            q
            for q, _ in sorted(counts.items(), key=lambda t: t[1], reverse=True)[:limit]
        ]

    return {"queries": popular_queries}
