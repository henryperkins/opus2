# backend/app/services/vector_service.py
"""Simplified vector service using PostgreSQL+pgvector only."""
import logging
from typing import List, Dict, Optional, Any
import numpy as np
from app.config import settings
from app.services.postgres_vector_service import PostgresVectorService

logger = logging.getLogger(__name__)


class VectorService:
    """Simplified vector service - PostgreSQL+pgvector only."""

    def __init__(self):
        self._backend: PostgresVectorService = PostgresVectorService()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the vector service."""
        if self._initialized:
            return

        await self._backend.initialize()
        self._initialized = True
        logger.info("Vector service initialized with pgvector backend")

    async def insert_embeddings(
        self, embeddings: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert embeddings with metadata."""
        await self.initialize()
        return await self._backend.insert_embeddings(embeddings)

    async def search(
        self,
        query_vector: np.ndarray,
        limit: Optional[int] = None,
        project_ids: Optional[List[int]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        await self.initialize()

        # Use defaults from settings if not provided
        if limit is None:
            limit = settings.vector_search_limit
        if score_threshold is None:
            score_threshold = settings.vector_score_threshold

        return await self._backend.search(
            query_vector=query_vector,
            limit=limit,
            project_ids=project_ids,
            score_threshold=score_threshold
        )

    async def delete_by_document(self, document_id: int) -> None:
        """Delete all embeddings for a document."""
        await self.initialize()
        await self._backend.delete_by_document(document_id)

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        await self.initialize()
        stats = await self._backend.get_stats()
        stats["configured_backend"] = "pgvector"
        return stats

    async def _get_backend(self) -> PostgresVectorService:
        """Get the backend instance for internal operations."""
        await self.initialize()
        return self._backend

    # Legacy compatibility methods for knowledge operations
    async def search_knowledge(
        self,
        query_embedding: List[float],
        project_ids: Optional[List[int]] = None,
        limit: int = 10,
        score_threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge embeddings using pgvector backend."""
        import numpy as np
        from sqlalchemy import text
        from app.database import AsyncSessionLocal

        try:
            query_vector = np.array(query_embedding)

            # Convert to pgvector format
            vector_str = "[" + ",".join(f"{x:.6f}" for x in query_vector.tolist()) + "]"

            async with AsyncSessionLocal() as db:
                # Build query using **named** parameters so SQLAlchemy receives a single
                # dictionary instead of a bare tuple (which triggers the “List argument
                # must consist only of tuples or dictionaries” error).
                if project_ids:
                    query_sql = """
                    SELECT
                        id,
                        metadata,
                        content,
                        1 - (embedding <=> CAST(:vector AS vector)) AS similarity_score
                    FROM embeddings
                    WHERE metadata->>'project_id' = ANY(:project_ids)
                      AND metadata->>'category' IS NOT NULL
                    ORDER BY embedding <=> CAST(:vector AS vector)
                    LIMIT :limit
                    """
                    params = {
                        "vector": vector_str,
                        "project_ids": [str(pid) for pid in project_ids],
                        "limit": limit,
                    }
                else:
                    query_sql = """
                    SELECT
                        id,
                        metadata,
                        content,
                        1 - (embedding <=> CAST(:vector AS vector)) AS similarity_score
                    FROM embeddings
                    WHERE metadata->>'category' IS NOT NULL
                    ORDER BY embedding <=> CAST(:vector AS vector)
                    LIMIT :limit
                    """
                    params = {
                        "vector": vector_str,
                        "limit": limit,
                    }

                # Execute with named parameters
                result = await db.execute(text(query_sql), params)
                rows = result.fetchall()

                knowledge_results = []
                for row in rows:
                    if row.similarity_score >= score_threshold:
                        # Parse metadata
                        metadata = row.metadata or {}
                        knowledge_results.append({
                            "id": str(row.id),
                            "content": row.content,
                            "score": float(row.similarity_score),
                            "title": metadata.get("title", "Untitled"),
                            "source": metadata.get("source", "Unknown"),
                            "category": metadata.get("category", "general"),
                            "project_id": int(metadata.get("project_id", 0)) if metadata.get("project_id") else None,
                            "metadata": metadata
                        })

                logger.info(f"Found {len(knowledge_results)} knowledge results for query")
                return knowledge_results

        except Exception as e:
            logger.error(f"Knowledge search failed: {e}", exc_info=True)
            return []

    async def search_code(
        self,
        query_embedding: List[float],
        project_ids: Optional[List[int]] = None,
        language: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search code embeddings using pgvector backend."""
        import numpy as np
        query_vector = np.array(query_embedding)
        results = await self.search(
            query_vector=query_vector,
            limit=limit,
            project_ids=project_ids,
            score_threshold=score_threshold
        )
        return results

    async def add_knowledge_entry(
        self,
        entry_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Add knowledge entry using pgvector backend."""
        try:
            from app.database import AsyncSessionLocal
            from sqlalchemy import text
            import hashlib

            # Create content hash for deduplication
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            async with AsyncSessionLocal() as db:
                # Insert into embeddings table with knowledge metadata
                insert_sql = """
                INSERT INTO embeddings (embedding, content, content_hash, metadata, created_at)
                VALUES (:embedding::vector, :content, :content_hash, :metadata::jsonb, NOW())
                ON CONFLICT (content_hash)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    created_at = NOW()
                """

                # Ensure project_id is in metadata for filtering
                full_metadata = {**metadata}
                if "project_id" not in full_metadata and "project_id" in metadata:
                    full_metadata["project_id"] = metadata["project_id"]

                # Add entry_id to metadata for reference
                full_metadata["entry_id"] = entry_id
                full_metadata["type"] = "knowledge"

                params = {
                    "embedding": embedding,
                    "content": content,
                    "content_hash": content_hash,
                    "metadata": full_metadata
                }

                await db.execute(text(insert_sql), params)
                await db.commit()

                logger.info(f"Added knowledge entry to pgvector: {entry_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to add knowledge entry: {e}", exc_info=True)
            return False


# Global instance
vector_service = VectorService()


async def get_vector_service() -> VectorService:
    """Dependency injection for vector service."""
    return vector_service
