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
        # For now, knowledge search is not implemented in pgvector backend
        # This should be extended when knowledge is migrated to pgvector
        logger.warning("Knowledge search not yet implemented for pgvector backend")
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
        # For now, knowledge entries are not implemented in pgvector backend
        # This should be extended when knowledge is migrated to pgvector
        logger.warning("Knowledge entries not yet implemented for pgvector backend")
        return False


# Global instance
vector_service = VectorService()


async def get_vector_service() -> VectorService:
    """Dependency injection for vector service."""
    return vector_service
