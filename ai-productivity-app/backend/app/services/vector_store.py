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
    """SQLite VSS vector store for embeddings with fallback to JSON storage."""

    def __init__(self, db_path: str = "data/vss.db"):
        self.db_path = db_path
        self.vss_available = False
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Get database connection with VSS loaded if available."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            if not hasattr(self, '_vss_checked'):
                self._vss_checked = True
                try:
                    # Try to load VSS extension
                    conn.enable_load_extension(True)
                    conn.load_extension("vector0")
                    conn.enable_load_extension(False)
                    self.vss_available = True
                    logger.info("SQLite VSS extension loaded successfully")
                except Exception as e:
                    logger.warning(f"VSS extension not available, using fallback: {e}")
                    self.vss_available = False
            elif self.vss_available:
                conn.enable_load_extension(True)
                conn.load_extension("vector0")
                conn.enable_load_extension(False)
            
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initialize tables based on VSS availability."""
        with self._get_connection() as conn:
            if self.vss_available:
                # Create VSS virtual table for embeddings
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS vss_embeddings USING vss0(
                        embedding(1536)
                    )
                    """
                )
            else:
                # Fallback table for embeddings stored as JSON
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS embeddings_fallback (
                        rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                        embedding TEXT NOT NULL
                    )
                    """
                )
            
            # Create metadata table (common for both modes)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_metadata (
                    rowid INTEGER PRIMARY KEY,
                    document_id INTEGER NOT NULL,
                    chunk_id INTEGER,
                    project_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Create indexes for better performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_embedding_metadata_document_id ON embedding_metadata(document_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_embedding_metadata_project_id ON embedding_metadata(project_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_embedding_metadata_content_hash ON embedding_metadata(content_hash)"
            )
            
            conn.commit()

    async def insert_embeddings(
        self, embeddings: List[Tuple[np.ndarray, Dict]]
    ) -> List[int]:
        """Insert embeddings with metadata."""
        rowids = []

        with self._get_connection() as conn:
            for embedding, metadata in embeddings:
                if self.vss_available:
                    # Insert into VSS table
                    cursor = conn.execute(
                        "INSERT INTO vss_embeddings(rowid, embedding) VALUES (NULL, ?)",
                        (embedding.astype(np.float32).tobytes(),),
                    )
                    rowid = cursor.lastrowid
                else:
                    # Insert into fallback table
                    cursor = conn.execute(
                        "INSERT INTO embeddings_fallback(embedding) VALUES (?)",
                        (json.dumps(embedding.tolist()),),
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
        if self.vss_available:
            return await self._search_vss(query_embedding, limit, project_ids, distance_type)
        else:
            return await self._search_fallback(query_embedding, limit, project_ids, distance_type)

    async def _search_vss(
        self,
        query_embedding: np.ndarray,
        limit: int,
        project_ids: Optional[List[int]],
        distance_type: str,
    ) -> List[Dict]:
        """VSS-powered search."""
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
                        "score": 1.0 - row["distance"],  # Convert distance to similarity
                        "document_id": row["document_id"],
                        "chunk_id": row["chunk_id"],
                        "project_id": row["project_id"],
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"]),
                    }
                )

        return results

    async def _search_fallback(
        self,
        query_embedding: np.ndarray,
        limit: int,
        project_ids: Optional[List[int]],
        distance_type: str,
    ) -> List[Dict]:
        """Fallback cosine similarity search."""
        results = []

        with self._get_connection() as conn:
            # Build base query
            query = """
                SELECT
                    e.rowid,
                    e.embedding,
                    m.document_id,
                    m.chunk_id,
                    m.project_id,
                    m.content,
                    m.metadata
                FROM embeddings_fallback e
                JOIN embedding_metadata m ON e.rowid = m.rowid
            """
            
            params = []
            
            # Add project filter
            if project_ids:
                query += " WHERE m.project_id IN ({})".format(
                    ",".join("?" * len(project_ids))
                )
                params.extend(project_ids)

            cursor = conn.execute(query, params)
            
            # Calculate similarities in Python
            similarities = []
            for row in cursor:
                try:
                    stored_embedding = np.array(json.loads(row["embedding"]))
                    
                    if distance_type == "cosine":
                        # Cosine similarity
                        dot_product = np.dot(query_embedding, stored_embedding)
                        norm_product = np.linalg.norm(query_embedding) * np.linalg.norm(stored_embedding)
                        similarity = dot_product / norm_product if norm_product > 0 else 0
                    else:
                        # L2 distance converted to similarity
                        distance = np.linalg.norm(query_embedding - stored_embedding)
                        similarity = 1.0 / (1.0 + distance)  # Convert distance to similarity
                    
                    similarities.append((similarity, row))
                except Exception as e:
                    logger.warning(f"Error calculating similarity: {e}")
                    continue
            
            # Sort by similarity and take top results
            similarities.sort(key=lambda x: x[0], reverse=True)
            
            for similarity, row in similarities[:limit]:
                results.append(
                    {
                        "rowid": row["rowid"],
                        "score": similarity,
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
                placeholders = ",".join("?" * len(rowids))
                
                if self.vss_available:
                    # Delete from VSS table
                    conn.execute(
                        f"DELETE FROM vss_embeddings WHERE rowid IN ({placeholders})",
                        rowids,
                    )
                else:
                    # Delete from fallback table
                    conn.execute(
                        f"DELETE FROM embeddings_fallback WHERE rowid IN ({placeholders})",
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
            if self.vss_available:
                conn.execute(
                    "UPDATE vss_embeddings SET embedding = ? WHERE rowid = ?",
                    (embedding.astype(np.float32).tobytes(), rowid),
                )
            else:
                conn.execute(
                    "UPDATE embeddings_fallback SET embedding = ? WHERE rowid = ?",
                    (json.dumps(embedding.tolist()), rowid),
                )
            conn.commit()

    async def get_stats(self) -> Dict:
        """Get vector store statistics."""
        with self._get_connection() as conn:
            # Count total embeddings
            if self.vss_available:
                cursor = conn.execute("SELECT COUNT(*) as count FROM vss_embeddings")
            else:
                cursor = conn.execute("SELECT COUNT(*) as count FROM embeddings_fallback")
            
            total_embeddings = cursor.fetchone()["count"]
            
            # Count by project
            cursor = conn.execute("""
                SELECT project_id, COUNT(*) as count 
                FROM embedding_metadata 
                GROUP BY project_id
            """)
            
            by_project = {row["project_id"]: row["count"] for row in cursor}
            
            return {
                "total_embeddings": total_embeddings,
                "by_project": by_project,
                "vss_enabled": self.vss_available,
                "db_path": self.db_path
            }

    async def cleanup_orphaned_embeddings(self) -> int:
        """Clean up embeddings that have no corresponding metadata."""
        with self._get_connection() as conn:
            if self.vss_available:
                # Find orphaned VSS embeddings
                cursor = conn.execute("""
                    SELECT v.rowid FROM vss_embeddings v
                    LEFT JOIN embedding_metadata m ON v.rowid = m.rowid
                    WHERE m.rowid IS NULL
                """)
                orphaned_rowids = [row["rowid"] for row in cursor]
                
                if orphaned_rowids:
                    placeholders = ",".join("?" * len(orphaned_rowids))
                    conn.execute(f"DELETE FROM vss_embeddings WHERE rowid IN ({placeholders})", orphaned_rowids)
            else:
                # Find orphaned fallback embeddings
                cursor = conn.execute("""
                    SELECT e.rowid FROM embeddings_fallback e
                    LEFT JOIN embedding_metadata m ON e.rowid = m.rowid
                    WHERE m.rowid IS NULL
                """)
                orphaned_rowids = [row["rowid"] for row in cursor]
                
                if orphaned_rowids:
                    placeholders = ",".join("?" * len(orphaned_rowids))
                    conn.execute(f"DELETE FROM embeddings_fallback WHERE rowid IN ({placeholders})", orphaned_rowids)
            
            conn.commit()
            return len(orphaned_rowids) if 'orphaned_rowids' in locals() else 0
