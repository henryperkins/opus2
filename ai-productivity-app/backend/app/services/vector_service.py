# backend/app/services/vector_service.py
"""Unified vector service with backend switching."""
import logging
from typing import List, Dict, Optional, Any, Protocol
import numpy as np
from app.config import settings
from app.services.postgres_vector_service import PostgresVectorService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)


class VectorServiceProtocol(Protocol):
    """Protocol defining the interface for vector database services."""

    async def initialize(self) -> None:
        ...

    async def insert_embeddings(self, embeddings: List[Dict[str, Any]]) -> List[str]:
        ...

    async def search(
        self,
        query_vector: np.ndarray,
        limit: int,
        project_ids: Optional[List[int]],
        score_threshold: Optional[float],
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        ...

    async def delete_by_document(self, document_id: int) -> None:
        ...



    async def get_stats(self) -> Dict[str, Any]:
        ...


class VectorService:
    """Factory for vector services."""

    def __init__(self):
        self._backend: VectorServiceProtocol
        if settings.vector_store_type == "qdrant":
            self._backend = QdrantService(collection="embeddings")
        elif settings.vector_store_type == "pgvector":
            self._backend = PostgresVectorService()
        else:
            raise ValueError(f"Unsupported vector_store_type: {settings.vector_store_type}")
        self._initialized = False
        logger.info(f"VectorService initialized with backend: {settings.vector_store_type}")

    async def initialize(self) -> None:
        """Initialize the vector service."""
        if self._initialized:
            return
        await self._backend.initialize()
        self._initialized = True
        logger.info(f"Vector service initialized with {settings.vector_store_type} backend")

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
        stats["configured_backend"] = settings.vector_store_type
        return stats

    async def get_backend(self) -> VectorServiceProtocol:
        """Get the underlying vector backend for advanced operations."""
        await self.initialize()
        return self._backend

# Global instance
vector_service = VectorService()


async def get_vector_service() -> VectorService:
    """Dependency injection for vector service."""
    return vector_service
