# backend/app/services/vector_service.py
"""Unified vector service that supports both SQLite VSS and Qdrant."""
import logging
from typing import List, Dict, Optional, Any, Protocol
import numpy as np
from app.config import settings

logger = logging.getLogger(__name__)


class VectorServiceProtocol(Protocol):
    """Protocol defining the interface for vector services."""

    async def initialize(self) -> None:
        """Initialize the vector service."""
        ...

    async def insert_embeddings(
        self, embeddings: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert embeddings with metadata."""
        ...

    async def search(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        project_ids: Optional[List[int]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        ...

    async def delete_by_document(self, document_id: int) -> None:
        """Delete all embeddings for a document."""
        ...

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        ...


class VectorService:
    """Unified vector service with automatic backend selection."""

    def __init__(self):
        self._backend: Optional[VectorServiceProtocol] = None
        self._initialized = False

    async def _get_backend(self) -> VectorServiceProtocol:
        """Get the configured vector backend."""
        if self._backend is not None:
            return self._backend

        if settings.vector_store_type.lower() == "qdrant":
            try:
                from app.services.qdrant_service import QdrantService
                self._backend = QdrantService(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port
                )
                logger.info("Using Qdrant vector backend")
            except ImportError as e:
                logger.warning(
                    f"Qdrant not available, falling back to SQLite VSS: {e}"
                )
                self._backend = await self._get_sqlite_backend()
        else:
            self._backend = await self._get_sqlite_backend()

        return self._backend

    async def _get_sqlite_backend(self) -> VectorServiceProtocol:
        """Get SQLite VSS backend with adapter."""
        from app.services.vector_store import VectorStore

        class SQLiteVSSAdapter:
            """Adapter to make VectorStore compatible with protocol."""

            def __init__(self):
                self.store = VectorStore()

            async def initialize(self) -> None:
                """SQLite VSS is initialized on creation."""
                pass

            async def insert_embeddings(
                self, embeddings: List[Dict[str, Any]]
            ) -> List[str]:
                """Insert embeddings using SQLite VSS format."""
                # Convert to SQLite VSS format
                sqlite_embeddings = []
                for emb in embeddings:
                    metadata = {
                        "document_id": emb.get("document_id"),
                        "project_id": emb.get("project_id"),
                        "chunk_id": emb.get("chunk_id"),
                        "content": emb.get("content", ""),
                        "content_hash": emb.get("content_hash", ""),
                    }
                    sqlite_embeddings.append((emb["vector"], metadata))

                rowids = await self.store.insert_embeddings(sqlite_embeddings)
                return [str(rid) for rid in rowids]

            async def search(
                self,
                query_vector: np.ndarray,
                limit: int = 10,
                project_ids: Optional[List[int]] = None,
                score_threshold: Optional[float] = None,
            ) -> List[Dict[str, Any]]:
                """Search using SQLite VSS."""
                results = await self.store.search(
                    query_embedding=query_vector,
                    limit=limit,
                    project_ids=project_ids,
                    distance_type="cosine"
                )

                # Filter by score threshold if provided
                if score_threshold is not None:
                    results = [
                        r for r in results
                        if r.get("score", 0) >= score_threshold
                    ]

                return results

            async def delete_by_document(self, document_id: int) -> None:
                """Delete embeddings by document ID."""
                await self.store.delete_by_document(document_id)

            async def get_stats(self) -> Dict[str, Any]:
                """Get statistics."""
                stats = await self.store.get_stats()
                stats["backend"] = "sqlite_vss"
                return stats

        adapter = SQLiteVSSAdapter()
        logger.info("Using SQLite VSS vector backend")
        return adapter

    async def initialize(self) -> None:
        """Initialize the vector service."""
        if self._initialized:
            return

        backend = await self._get_backend()
        await backend.initialize()
        self._initialized = True
        logger.info("Vector service initialized")

    async def insert_embeddings(
        self, embeddings: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert embeddings with metadata."""
        await self.initialize()
        backend = await self._get_backend()
        return await backend.insert_embeddings(embeddings)

    async def search(
        self,
        query_vector: np.ndarray,
        limit: Optional[int] = None,
        project_ids: Optional[List[int]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        await self.initialize()
        backend = await self._get_backend()

        # Use defaults from settings if not provided
        if limit is None:
            limit = settings.vector_search_limit
        if score_threshold is None:
            score_threshold = settings.vector_score_threshold

        return await backend.search(
            query_vector=query_vector,
            limit=limit,
            project_ids=project_ids,
            score_threshold=score_threshold
        )

    async def delete_by_document(self, document_id: int) -> None:
        """Delete all embeddings for a document."""
        await self.initialize()
        backend = await self._get_backend()
        await backend.delete_by_document(document_id)

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        await self.initialize()
        backend = await self._get_backend()
        stats = await backend.get_stats()
        stats["configured_backend"] = settings.vector_store_type
        return stats


# Global instance
vector_service = VectorService()


async def get_vector_service() -> VectorService:
    """Dependency injection for vector service."""
    return vector_service
