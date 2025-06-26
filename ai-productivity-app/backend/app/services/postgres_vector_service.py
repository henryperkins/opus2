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

import numpy as np
import sqlalchemy as sa
from sqlalchemy.engine import Engine  # Connection import removed (was unused)

from app.config import settings
from app.database import get_engine_sync  # helper that returns a *sync* engine

logger = logging.getLogger(__name__)


class PostgresVectorService:
    """pgvector implementation compatible with VectorServiceProtocol."""

    def __init__(self) -> None:
        self.table_name: str = getattr(
            settings, "postgres_vector_table", "code_embedding_vectors"
        )
        # We *must* use a synchronous engine because SQLAlchemy async
        # engines do not currently support the `vector` binary format
        # conversion without extra work.  All calls are tiny compared to
        # network round-trip time -> sync is acceptable.
        self.engine: Engine = get_engine_sync(echo=False)

    # --------------------------------------------------------------------- #
    # Initialisation                                                        #
    # --------------------------------------------------------------------- #

    async def initialize(self) -> None:  # noqa: D401
        """Create extension / table / indexes idempotently."""
        with self.engine.begin() as conn:  # type: Connection
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")

            conn.exec_driver_sql(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id           SERIAL PRIMARY KEY,
                    document_id  INTEGER      NOT NULL,
                    chunk_id     INTEGER,
                    project_id   INTEGER      NOT NULL,
                    embedding    vector(1536) NOT NULL,
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

        where_fragments: List[str] = []
        params: Dict[str, Any] = {"query_vec": self._to_pgvector(query_vector), "limit": limit}

        if project_ids:
            where_fragments.append("project_id = ANY(:pids)")
            params["pids"] = project_ids  # psycopg2 maps list → Postgres array

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

    # --------------------------------------------------------------------- #
    # Delete / stats                                                        #
    # --------------------------------------------------------------------- #

    async def delete_by_document(self, document_id: int) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                sa.text(f"DELETE FROM {self.table_name} WHERE document_id = :doc"),
                {"doc": document_id},
            )

    async def get_stats(self) -> Dict[str, Any]:
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
            "backend": "postgres",
            "table": self.table_name,
            "total_embeddings": total,
            "by_project": by_project,
        }
