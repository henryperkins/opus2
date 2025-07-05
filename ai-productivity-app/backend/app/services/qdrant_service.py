"""Async façade over Qdrant for embeddings & semantic search."""

from __future__ import annotations

import concurrent.futures
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import anyio
from qdrant_client import QdrantClient, models
from prometheus_client import Summary, Gauge

from app.config import settings
# Avoid circular import - define protocol locally or use TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.services.vector_service import VectorServiceProtocol

logger = logging.getLogger(__name__)

__all__ = ["QdrantService"]

VECTOR_UPSERT_LAT = Summary("vector_upsert_seconds", "Qdrant upsert latency")
VECTOR_SEARCH_LAT = Summary("vector_search_seconds", "Qdrant search latency")
VECTOR_DELETE_LAT = Summary("vector_delete_seconds", "Qdrant delete latency")
VECTOR_POINTS_COUNT = Gauge("vector_points_total", "Total points in Qdrant", ["collection"])


def _run_blocking(func, /, *args, **kwargs):
    """Execute *func* in the global thread-pool while preserving kwargs."""
    if kwargs:
        return anyio.to_thread.run_sync(lambda: func(*args, **kwargs))
    return anyio.to_thread.run_sync(func, *args)


class QdrantService:
    """Async-friendly wrapper around Qdrant collections."""

    _EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None

    def __init__(
        self,
        *,
        collection: str = "kb_entries",
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        vector_size: int | None = None,
    ) -> None:
        if QdrantService._EXECUTOR is None:
            QdrantService._EXECUTOR = concurrent.futures.ThreadPoolExecutor(
                max_workers=settings.qdrant_max_workers or 16,
                thread_name_prefix="qdrant",
            )

        self.collection_name = collection
        self.vector_size = vector_size or settings.qdrant_vector_size
        self.client = QdrantClient(
            url=url or settings.qdrant_url,
            api_key=api_key or settings.qdrant_api_key,
            timeout=settings.qdrant_timeout or 30,
        )

    async def initialize(self) -> None:
        """Initialize the Qdrant service by creating the collection if it doesn't exist."""
        await self._create_collection_if_missing()

    async def _create_collection_if_missing(self) -> None:
        """Create the Qdrant collection if it does not already exist."""
        collections = await _run_blocking(self.client.get_collections)
        names = [c.name for c in collections.collections]
        if self.collection_name in names:
            logger.info("Qdrant collection '%s' exists", self.collection_name)
            return

        await _run_blocking(
            self.client.create_collection,
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE
            ),
            hnsw_config=models.HnswConfigDiff(m=16, ef_construct=200),
        )
        logger.info("Created Qdrant collection '%s'", self.collection_name)

    @VECTOR_UPSERT_LAT.time()
    async def insert_embeddings(self, embeddings: List[Dict[str, Any]]) -> List[str]:
        """Insert embeddings into the Qdrant collection."""
        points = [
            models.PointStruct(
                id=e["id"],
                vector=e["vector"],
                payload={
                    "document_id": e.get("document_id"),
                    "project_id": e.get("project_id"),
                    "content": e.get("content", ""),
                    "chunk_id": e.get("chunk_id"),
                    "metadata": e.get("metadata", {}),
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
            for e in embeddings
        ]

        result = await _run_blocking(
            self.client.upsert,
            collection_name=self.collection_name,
            points=points,
        )
        if result.status != models.UpdateStatus.COMPLETED:
            logger.error("Qdrant upsert failed (%s)", result.status)
        
        VECTOR_POINTS_COUNT.labels(collection=self.collection_name).inc(len(points))
        return [str(p.id) for p in points]

    @VECTOR_SEARCH_LAT.time()
    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        project_ids: Optional[List[int]] = None,
        score_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in the Qdrant collection."""
        must_conditions = []
        if project_ids:
            must_conditions.append(
                models.FieldCondition(
                    key="project_id",
                    match=models.MatchAny(any=project_ids)
                )
            )
        if filters:
            for key, value in filters.items():
                if value is not None:
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                    )
        
        filt = models.Filter(must=must_conditions) if must_conditions else None

        results = await _run_blocking(
            self.client.search,
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=filt,
            limit=limit,
            score_threshold=score_threshold,
        )
        return [
            {
                "id": r.id,
                "score": r.score,
                **r.payload,
            }
            for r in results
        ]

    @VECTOR_DELETE_LAT.time()
    async def delete_by_document(self, document_id: int) -> None:
        """Delete vectors associated with a specific document ID."""
        await _run_blocking(
            self.client.delete,
            collection_name=self.collection_name,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id)
                    )
                ]
            ),
        )
        logger.info("Removed vectors for document %s from '%s'", document_id, self.collection_name)

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the Qdrant collection."""
        info = await _run_blocking(self.client.get_collection, self.collection_name)
        stats = {
            "backend": "qdrant",
            "total_embeddings": info.points_count or 0,
            "collection_name": self.collection_name,
        }
        
        # Handle vector configuration based on the actual structure
        if hasattr(info, 'config') and hasattr(info.config, 'params'):
            # Handle VectorParams structure
            vector_config = info.config.params
            if hasattr(vector_config, 'size'):
                stats["vector_size"] = vector_config.size
            if hasattr(vector_config, 'distance'):
                stats["distance_metric"] = vector_config.distance
        elif hasattr(info, 'vectors_config'):
            # Handle alternative structure
            if hasattr(info.vectors_config, 'params'):
                params = info.vectors_config.params
                if hasattr(params, 'size'):
                    stats["vector_size"] = params.size
                if hasattr(params, 'distance'):
                    stats["distance_metric"] = params.distance
        
        if info.points_count is not None:
            VECTOR_POINTS_COUNT.labels(collection=self.collection_name).set(info.points_count)
        return stats

    async def gc_dangling_points(self) -> int:
        """Garbage collect dangling vector points that no longer exist in the database."""
        from app.models.code import CodeEmbedding
        from app.database import SessionLocal
        
        removed_count = 0
        
        try:
            qdrant_ids = await _run_blocking(
                lambda: {str(p.id) for p in self.client.scroll(
                    collection_name=self.collection_name,
                    limit=10000,
                    with_payload=False,
                    with_vectors=False
                )[0]}
            )
            
            with SessionLocal() as db:
                db_ids = {str(row[0]) for row in db.query(CodeEmbedding.id).all()}
            
            stale_ids = qdrant_ids - db_ids
            
            if stale_ids:
                logger.info(f"Found {len(stale_ids)} stale embeddings to remove")
                await _run_blocking(
                    self.client.delete,
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(points=list(stale_ids))
                )
                removed_count = len(stale_ids)
                logger.info(f"Removed {len(stale_ids)} stale embeddings")
                    
        except Exception as exc:
            logger.error(f"GC failed: {exc}")
        
        return removed_count

    @classmethod
    def shutdown(cls) -> None:
        """Shutdown the shared thread pool executor."""
        if cls._EXECUTOR is not None:
            logger.info("Shutting down QdrantService thread pool executor")
            cls._EXECUTOR.shutdown(wait=True)
            cls._EXECUTOR = None
