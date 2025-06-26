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
                # Use the more complete QdrantVectorStore instead of QdrantService
                self._backend = await self._get_qdrant_backend()
            except ImportError as e:
                logger.warning(
                    "Qdrant not available, falling back to pgvector: %s", e
                )
                self._backend = await self._get_pgvector_backend()
        elif settings.vector_store_type.lower() == "pgvector":
            self._backend = await self._get_pgvector_backend()
        elif settings.vector_store_type.lower() == "sqlite_vss":
            # SQLite VSS is deprecated and not fully implemented
            raise NotImplementedError(
                "SQLite VSS backend is deprecated and not fully implemented. "
                "Please use 'pgvector' or 'qdrant' instead."
            )
        else:
            # Default to pgvector
            logger.info("Using default pgvector backend")
            self._backend = await self._get_pgvector_backend()

        return self._backend

    async def _get_qdrant_backend(self) -> VectorServiceProtocol:
        """Get Qdrant backend with adapter."""
        from app.vector_store.qdrant_client import QdrantVectorStore
        
        class QdrantVectorStoreAdapter:
            """Adapter to make QdrantVectorStore compatible with protocol."""
            
            def __init__(self):
                self.store = QdrantVectorStore()
            
            async def initialize(self) -> None:
                """Initialize Qdrant collections."""
                await self.store.init_collections()
            
            async def insert_embeddings(
                self, embeddings: List[Dict[str, Any]]
            ) -> List[str]:
                """Insert code embeddings using Qdrant format."""
                # Use code embedding method
                results = []
                for emb in embeddings:
                    success = await self.store.add_code_embedding(
                        chunk_id=emb["chunk_id"],
                        embedding=emb["vector"],
                        metadata={
                            "document_id": emb.get("document_id"),
                            "project_id": emb.get("project_id"),
                            "file_path": emb.get("file_path", ""),
                            "language": emb.get("language", ""),
                            "symbol_name": emb.get("symbol_name", ""),
                            "symbol_type": emb.get("symbol_type", ""),
                            "start_line": emb.get("start_line", 0),
                            "end_line": emb.get("end_line", 0),
                            "content": emb.get("content", ""),
                        }
                    )
                    if success:
                        results.append(str(emb["chunk_id"]))
                return results
            
            async def search(
                self,
                query_vector: np.ndarray,
                limit: int = 10,
                project_ids: Optional[List[int]] = None,
                score_threshold: Optional[float] = None,
            ) -> List[Dict[str, Any]]:
                """Search using Qdrant code search."""
                return await self.store.search_code(
                    query_embedding=query_vector.tolist(),
                    project_ids=project_ids,
                    limit=limit,
                    score_threshold=score_threshold or 0.7
                )
            
            async def delete_by_document(self, document_id: int) -> None:
                """Delete embeddings by document - not directly supported by QdrantVectorStore."""
                # QdrantVectorStore only supports delete by project, not by document
                # This is a limitation we need to address
                logger.warning(f"Document-level deletion not supported by QdrantVectorStore for document {document_id}")
            
            async def get_stats(self) -> Dict[str, Any]:
                """Get statistics."""
                stats = await self.store.get_stats()
                stats["backend"] = "qdrant"
                return stats
        
        adapter = QdrantVectorStoreAdapter()
        logger.info("Using Qdrant vector backend")
        return adapter

    async def _get_pgvector_backend(self) -> VectorServiceProtocol:
        """Get PostgreSQL+pgvector backend."""
        from app.services.postgres_vector_service import PostgresVectorService
        
        backend = PostgresVectorService()
        logger.info("Using PostgreSQL+pgvector backend")
        return backend

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

    # Knowledge service interface methods for compatibility
    async def search_knowledge(
        self,
        query_embedding: List[float],
        project_ids: Optional[List[int]] = None,
        limit: int = 10,
        score_threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge embeddings - delegates to appropriate backend."""
        # Check if we have Qdrant backend
        if settings.vector_store_type.lower() == "qdrant":
            try:
                from app.vector_store.qdrant_client import QdrantVectorStore
                qdrant = QdrantVectorStore()
                await qdrant.init_collections()
                return await qdrant.search_knowledge(
                    query_embedding=query_embedding,
                    project_ids=project_ids,
                    limit=limit,
                    score_threshold=score_threshold,
                    filters=filters
                )
            except Exception as e:
                logger.warning(f"Qdrant knowledge search failed: {e}")
                return []
        
        # For pgvector and other backends, knowledge search is not yet implemented
        # This should be extended to support knowledge in pgvector
        logger.warning(f"Knowledge search not implemented for {settings.vector_store_type} backend")
        return []

    async def search_code(
        self,
        query_embedding: List[float],
        project_ids: Optional[List[int]] = None,
        language: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search code embeddings - delegates to appropriate backend."""
        # Check if we have Qdrant backend
        if settings.vector_store_type.lower() == "qdrant":
            try:
                from app.vector_store.qdrant_client import QdrantVectorStore
                qdrant = QdrantVectorStore()
                await qdrant.init_collections()
                return await qdrant.search_code(
                    query_embedding=query_embedding,
                    project_ids=project_ids,
                    language=language,
                    limit=limit,
                    score_threshold=score_threshold
                )
            except Exception as e:
                logger.warning(f"Qdrant code search failed, falling back to SQLite VSS: {e}")
                
        # Use existing SQLite VSS search
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
        """Add knowledge entry - delegates to Qdrant if available."""
        # Check if we have Qdrant backend
        if settings.vector_store_type.lower() == "qdrant":
            try:
                from app.vector_store.qdrant_client import QdrantVectorStore
                qdrant = QdrantVectorStore()
                await qdrant.init_collections()
                return await qdrant.add_knowledge_entry(
                    entry_id=entry_id,
                    content=content,
                    embedding=embedding,
                    metadata=metadata
                )
            except Exception as e:
                logger.warning(f"Qdrant knowledge add failed: {e}")
                return False
        
        # For SQLite VSS, knowledge entries are not supported yet
        logger.warning("Knowledge entries not supported with SQLite VSS backend")
        return False


# Global instance
vector_service = VectorService()


async def get_vector_service() -> VectorService:
    """Dependency injection for vector service."""
    return vector_service
