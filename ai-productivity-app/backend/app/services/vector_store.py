# backend/app/services/vector_store.py
"""SQLite VSS vector store implementation."""
import sqlite3
import numpy as np
from typing import List, Dict, Optional, Tuple
import json
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class VectorStore:
    """SQLite VSS vector store for embeddings."""

    def __init__(self, db_path: str = "data/vss.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get database connection with VSS loaded."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Load VSS extension
            conn.enable_load_extension(True)
            conn.load_extension("vector0")
            conn.enable_load_extension(False)
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize VSS tables if not exists."""
        with self._get_connection() as conn:
            # Create virtual table
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS vss_embeddings USING vss0(
                    embedding(1536)
                )
            """
            )
            conn.commit()

    async def insert_embeddings(
        self, embeddings: List[Tuple[np.ndarray, Dict]]
    ) -> List[int]:
        """Insert embeddings with metadata."""
        rowids = []

        with self._get_connection() as conn:
            for embedding, metadata in embeddings:
                # Insert into VSS table
                cursor = conn.execute(
                    "INSERT INTO vss_embeddings(rowid, embedding) VALUES (NULL, ?)",
                    (embedding.astype(np.float32).tobytes(),),
                )
                rowid = cursor.lastrowid
                rowids.append(rowid)

                # Insert metadata
                conn.execute(
                    """
                    INSERT INTO embedding_metadata
                    (rowid, document_id, chunk_id, project_id, content, content_hash, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        rowid,
                        metadata["document_id"],
                        metadata.get("chunk_id"),
                        metadata["project_id"],
                        metadata["content"],
                        metadata["content_hash"],
                        json.dumps(metadata),
                    ),
                )

            conn.commit()

        return rowids

    async def search(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        project_ids: Optional[List[int]] = None,
        distance_type: str = "cosine",
    ) -> List[Dict]:
        """Search for similar embeddings."""
        results = []

        with self._get_connection() as conn:
            # Build query
            if distance_type == "cosine":
                distance_func = "vss_distance_cosine"
            else:
                distance_func = "vss_distance_l2"

            query = f"""
                SELECT
                    v.rowid,
                    {distance_func}(v.embedding, ?) as distance,
                    m.document_id,
                    m.chunk_id,
                    m.project_id,
                    m.content,
                    m.metadata
                FROM vss_embeddings v
                JOIN embedding_metadata m ON v.rowid = m.rowid
                WHERE v.rowid IN (
                    SELECT rowid FROM vss_embeddings
                    WHERE vss_search(embedding, ?)
                    LIMIT ?
                )
            """

            params = [
                query_embedding.astype(np.float32).tobytes(),
                query_embedding.astype(np.float32).tobytes(),
                limit * 2,  # Get more for filtering
            ]

            # Add project filter
            if project_ids:
                query += " AND m.project_id IN ({})".format(
                    ",".join("?" * len(project_ids))
                )
                params.extend(project_ids)

            query += " ORDER BY distance ASC LIMIT ?"
            params.append(limit)

            # Execute search
            cursor = conn.execute(query, params)

            for row in cursor:
                results.append(
                    {
                        "rowid": row["rowid"],
                        "score": 1.0
                        - row["distance"],  # Convert distance to similarity
                        "document_id": row["document_id"],
                        "chunk_id": row["chunk_id"],
                        "project_id": row["project_id"],
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]),
                    }
                )

        return results

    async def delete_by_document(self, document_id: int):
        """Delete all embeddings for a document."""
        with self._get_connection() as conn:
            # Get rowids to delete
            cursor = conn.execute(
                "SELECT rowid FROM embedding_metadata WHERE document_id = ?",
                (document_id,),
            )
            rowids = [row["rowid"] for row in cursor]

            if rowids:
                # Delete from VSS
                placeholders = ",".join("?" * len(rowids))
                conn.execute(
                    f"DELETE FROM vss_embeddings WHERE rowid IN ({placeholders})",
                    rowids,
                )

                # Delete metadata
                conn.execute(
                    "DELETE FROM embedding_metadata WHERE document_id = ?",
                    (document_id,),
                )

                conn.commit()

    async def update_embedding(self, rowid: int, embedding: np.ndarray):
        """Update an existing embedding."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE vss_embeddings SET embedding = ? WHERE rowid = ?",
                (embedding.astype(np.float32).tobytes(), rowid),
            )
            conn.commit()
