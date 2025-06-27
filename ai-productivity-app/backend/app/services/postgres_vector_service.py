"""
PostgreSQL + pgvector backend for the unified VectorService.

This class implements the VectorServiceProtocol interface so that
`settings.vector_store_type = \"postgres\"` will route all embedding
storage / search calls to a *native* pgvector table instead of SQLite VSS
or Qdrant.

It intentionally keeps third-party requirements to a minimum – the only
server-side dependency is the **pgvector** extension already available on
modern Postgres ≥ 14 (Neon, Supabase, Timescale, Crunchy Bridge …).

Schema
------
Table ``code_embedding_vectors`` is created on-demand if it does not yet
exist:

    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS code_embedding_vectors (
        id           serial PRIMARY KEY,
        document_id  integer      NOT NULL,
        chunk_id     integer,
        project_id   integer      NOT NULL,
        embedding    vector(1536) NOT NULL,
        content      text         NOT NULL,
        content_hash text         NOT NULL,
        metadata     jsonb        NOT NULL,
        created_at   timestamptz  DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_vec_project
        ON code_embedding_vectors(project_id);
    -- Distance operator family is picked automatically
    CREATE INDEX IF NOT EXISTS idx_vec_ivfflat
        ON code_embedding_vectors
        USING ivfflat (embedding vector_cosine_ops);

If you prefer a different table name set ``POSTGRES_VECTOR_TABLE`` in
your ``backend/.env``; otherwise *code_embedding_vectors* is used.

Performance tips
----------------
* After initial population run ``ANALYZE`` so the planner knows the row
  count.
* For large datasets (> 1 M) increase ``ivfflat`` *lists*:

      CREATE INDEX … USING ivfflat … WITH (lists = 200);

* When you change the embedding dimension drop & recreate the index.

"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Optional anyio shim – mirrors approach in qdrant_client so the wider
# codebase can import *PostgresVectorService* even when the heavy *anyio*
# dependency is not installed in the execution environment (CI sandbox).
# The implementation provides only the minimal subset used here:
# ``anyio.to_thread.run_sync``.
# ---------------------------------------------------------------------------

# pylint: disable=import-error

try:
    import anyio  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – lightweight fallback for CI
    import sys as _sys
    import types as _types
    import asyncio as _asyncio

    _anyio = _types.ModuleType("anyio")

    class _ToThread:  # pylint: disable=too-few-public-methods
        """Subset of *anyio.to_thread* namespace used by this module."""

        @staticmethod
        async def run_sync(func, *args, **kwargs):  # type: ignore[override]
            loop = _asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)

    # Expose namespace objects expected by callers
    _anyio.to_thread = _ToThread()  # type: ignore[attr-defined]

    # Register stub so subsequent ``import anyio`` statements succeed
    _sys.modules["anyio"] = _anyio
    anyio = _anyio  # type: ignore
import numpy as np
import sqlalchemy as sa
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Optional pgvector shim – avoids pulling the heavy C-extension when the CI
# environment only needs to *import* the symbol so that SQLAlchemy models can
# be constructed.  When the real *pgvector* package is absent we register a
# *very small* placeholder that mimics the two attributes referenced in this
# file: ``Vector`` (SQLAlchemy column type) and ``vector_cosine_ops`` (index
# operator family).  All actual distance calculations happen inside Postgres
# so the stub never needs to implement them.
# ---------------------------------------------------------------------------

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – lightweight fallback for CI
    import sys as _sys
    import types as _types

    _pgvector_mod = _types.ModuleType("pgvector")
    _sa_mod = _types.ModuleType("pgvector.sqlalchemy")

    class _Vector:  # pylint: disable=too-few-public-methods
        """Stub replacement for pgvector.sqlalchemy.Vector """

        cache_ok = True

        def __init__(self, dimension: int):  # noqa: D401
            self.dimension = dimension

        # SQLAlchemy calls ``compile`` on the type to emit DDL – we return the
        # canonical postgres type here so migrations succeed.
        def compile(self, dialect=None):  # noqa: D401, ANN001
            return f"vector({self.dimension})"

    # Minimal operator family names as constants – only used when building
    # index DDL strings which are rendered server-side by SQLA.
    _sa_mod.Vector = _Vector  # type: ignore[attr-defined]

    # ``vector_cosine_ops`` is referenced literally in index creation.  It is
    # not an attribute but part of the returned DDL so we expose a constant in
    # the module namespace for completeness.
    _sa_mod.vector_cosine_ops = "vector_cosine_ops"  # type: ignore[attr-defined]

    _pgvector_mod.sqlalchemy = _sa_mod  # type: ignore[attr-defined]

    _sys.modules["pgvector"] = _pgvector_mod
    _sys.modules["pgvector.sqlalchemy"] = _sa_mod

    Vector = _Vector  # type: ignore

from app.config import settings
from app.database import get_engine_sync

logger = logging.getLogger(__name__)


class PostgresVectorService:
    """pgvector implementation compatible with VectorServiceProtocol."""

    def __init__(self) -> None:
        self.table_name: str = settings.postgres_vector_table
        self.vector_size: int = settings.embedding_vector_size
        # Use synchronous engine with anyio.to_thread for async compatibility
        self.engine: Engine = get_engine_sync(echo=False)

    # --------------------------------------------------------------------- #
    # Initialisation                                                        #
    # --------------------------------------------------------------------- #

    async def initialize(self) -> None:
        """Create extension / table / indexes idempotently."""
        def _setup_schema():
            with self.engine.begin() as conn:
                conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgvector;")

                conn.exec_driver_sql(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id           SERIAL PRIMARY KEY,
                        document_id  INTEGER      NOT NULL,
                        chunk_id     INTEGER,
                        project_id   INTEGER      NOT NULL,
                        embedding    vector({self.vector_size}) NOT NULL,
                        content      TEXT         NOT NULL,
                        content_hash TEXT         NOT NULL,
                        metadata     JSONB        NOT NULL,
                        created_at   TIMESTAMPTZ  DEFAULT NOW()
                    );
                    """
                )

                # Normal B-tree index for filtering by project
                conn.exec_driver_sql(
                    f"""CREATE INDEX IF NOT EXISTS idx_{self.table_name}_project
                           ON {self.table_name}(project_id);"""
                )

                # Approximate nearest-neighbour index (cosine distance)
                conn.exec_driver_sql(
                    f"""CREATE INDEX IF NOT EXISTS idx_{self.table_name}_ivfflat
                           ON {self.table_name}
                           USING ivfflat (embedding vector_cosine_ops);"""
                )

        await anyio.to_thread.run_sync(_setup_schema)
        logger.info("pgvector backend ready (table: %s)", self.table_name)

    # --------------------------------------------------------------------- #
    # Insert                                                                #
    # --------------------------------------------------------------------- #

    @staticmethod
    def _to_pgvector(vec: np.ndarray) -> str:
        """Convert numpy array (1-D) to pgvector literal."""
        # Use str.format to avoid f-string parsing issues within generator
        return "[" + ",".join("{:.6f}".format(x) for x in vec.tolist()) + "]"

    async def insert_embeddings(self, embeddings: List[Dict[str, Any]]) -> List[str]:
        def _insert():
            row_ids: List[str] = []
            with self.engine.begin() as conn:
                for emb in embeddings:
                    row = conn.execute(
                        sa.text(
                            f"""INSERT INTO {self.table_name}
                                   (document_id, chunk_id, project_id,
                                    embedding, content, content_hash, metadata)
                                   VALUES
                                   (:document_id, :chunk_id, :project_id,
                                    :embedding, :content, :content_hash, :metadata)
                                   RETURNING id"""
                        ),
                        {
                            "document_id": emb.get("document_id"),
                            "chunk_id": emb.get("chunk_id"),
                            "project_id": emb.get("project_id"),
                            "embedding": self._to_pgvector(emb["vector"]),
                            "content": emb.get("content", ""),
                            "content_hash": emb.get("content_hash", ""),
                            "metadata": json.dumps(emb, default=str),
                        },
                    ).scalar_one()
                    row_ids.append(str(row))
            return row_ids
        
        return await anyio.to_thread.run_sync(_insert)

    # --------------------------------------------------------------------- #
    # Search                                                                #
    # --------------------------------------------------------------------- #

    async def search(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        project_ids: Optional[List[int]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []

        def _search():
            where_fragments: List[str] = []
            params: Dict[str, Any] = {"query_vec": self._to_pgvector(query_vector), "limit": limit}

            if project_ids:
                where_fragments.append("project_id = ANY(:pids)")
                params["pids"] = project_ids

            sql_where = ("WHERE " + " AND ".join(where_fragments)) if where_fragments else ""
            sql = (
                f"""SELECT id,
                             document_id,
                             chunk_id,
                             project_id,
                             content,
                             metadata,
                             1 - (embedding <#> :query_vec) AS score
                      FROM {self.table_name}
                      {sql_where}
                      ORDER BY embedding <#> :query_vec
                      LIMIT :limit;"""
            )

            results: List[Dict[str, Any]] = []
            with self.engine.begin() as conn:
                for row in conn.execute(sa.text(sql), params):
                    score = float(row.score)
                    if score_threshold is not None and score < score_threshold:
                        continue
                    results.append(
                        {
                            "id": row.id,
                            "document_id": row.document_id,
                            "chunk_id": row.chunk_id,
                            "project_id": row.project_id,
                            "content": row.content,
                            "metadata": row.metadata,
                            "score": score,
                        }
                    )
            return results

        return await anyio.to_thread.run_sync(_search)

    # --------------------------------------------------------------------- #
    # Delete / stats                                                        #
    # --------------------------------------------------------------------- #

    async def delete_by_document(self, document_id: int) -> None:
        def _delete():
            with self.engine.begin() as conn:
                conn.execute(
                    sa.text(f"DELETE FROM {self.table_name} WHERE document_id = :doc"),
                    {"doc": document_id},
                )
        
        await anyio.to_thread.run_sync(_delete)

    async def get_stats(self) -> Dict[str, Any]:
        def _get_stats():
            with self.engine.begin() as conn:
                total = conn.execute(
                    sa.text(f"SELECT COUNT(*) FROM {self.table_name}")
                ).scalar_one()
                by_project = dict(
                    conn.execute(
                        sa.text(
                            f"SELECT project_id, COUNT(*) FROM {self.table_name} GROUP BY project_id"
                        )
                    ).fetchall()
                )
            return {
                "backend": "pgvector",
                "table": self.table_name,
                "total_embeddings": total,
                "by_project": by_project,
            }
        
        return await anyio.to_thread.run_sync(_get_stats)
