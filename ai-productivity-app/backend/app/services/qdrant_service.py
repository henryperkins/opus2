"""Async façade over Qdrant for embeddings & semantic search."""

from __future__ import annotations

import concurrent.futures
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import anyio

try:
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.http.models import (  # type: ignore
        Distance,
        FieldCondition,
        Filter,
        HnswConfigDiff,
        MatchAny,
        MatchValue,
        PointStruct,
        UpdateStatus,
        VectorParams,
    )
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ImportError(
        "The `qdrant-client` package is required. "
        "Install with: pip install qdrant-client>=1.9.0"
    ) from exc

from app.config import settings  # pylint: disable=import-error

logger = logging.getLogger(__name__)

__all__ = ["QdrantService"]


def _run_blocking(func, *args, **kwargs):
    """Run a blocking Qdrant call inside the shared thread-pool."""
    return anyio.to_thread.run_sync(func, *args, **kwargs)


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

    # ------------------------------------------------------------------ #
    # Bootstrap
    # ------------------------------------------------------------------ #
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
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE
            ),
            hnsw_config=HnswConfigDiff(m=16, ef_construct=200),
        )
        logger.info("Created Qdrant collection '%s'", self.collection_name)

    # ------------------------------------------------------------------ #
    # Upsert
    # ------------------------------------------------------------------ #
    async def upsert(self, embeddings: List[Dict[str, Any]]) -> List[str]:
        """Upsert embeddings into the Qdrant collection.

        Args:
            embeddings: List of dictionaries containing embedding data.

        Returns:
            List of IDs for the upserted points.
        """
        points = [
            PointStruct(
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
        if result.status != UpdateStatus.COMPLETED:  # type: ignore[attr-defined]
            logger.error(
                "Qdrant upsert failed (%s)",
                result.status
            )
        return [str(p.id) for p in points]

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    async def search(
        self,
        *,
        query_vector: List[float],
        limit: int = 10,
        project_ids: Optional[List[int]] = None,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in the Qdrant collection.

        Args:
            query_vector: Vector to search for similarities.
            limit: Maximum number of results to return.
            project_ids: Optional list of project IDs to filter results.
            score_threshold: Minimum similarity score for results.

        Returns:
            List of search results with IDs, scores, and payload data.
        """
        filt = (
            Filter(
                must=[
                    FieldCondition(
                        key="project_id",
                        match=MatchAny(any=project_ids)
                    )
                ]
            )
            if project_ids
            else None
        )

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

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #
    async def delete_by_document(self, document_id: int) -> None:
        """Delete vectors associated with a specific document ID.

        Args:
            document_id: ID of the document whose vectors should be deleted.
        """
        await _run_blocking(
            self.client.delete,
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            ),
        )
        logger.info(
            "Removed vectors for document %s from '%s'",
            document_id,
            self.collection_name
        )

    # ------------------------------------------------------------------ #
    # Stats
    # ------------------------------------------------------------------ #
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the Qdrant collection.

        Returns:
            Dictionary containing collection statistics.
        """
        info = await _run_blocking(self.client.get_collection, self.collection_name)
        return {
            "total_points": info.points_count,
            "vector_size": info.config.params.vectors.size,
            "distance_metric": info.config.params.vectors.distance,
            "collection_name": self.collection_name,
        }
