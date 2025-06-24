# app/vector_store/qdrant_client.py
"""
Strong-mode Qdrant vector store:
* Fails fast if `qdrant-client` isn't installed.
* Runs blocking I/O in a ThreadPoolExecutor so `async` callers remain non-blocking.
* Respects central settings for URL / API key / vector size.
"""

from __future__ import annotations

import concurrent.futures
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import anyio

try:
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.models import (  # type: ignore
        Distance,
        FieldCondition,
        Filter,
        MatchAny,
        MatchValue,
        PointStruct,
        UpdateStatus,
        VectorParams,
    )
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ImportError(
        "The `qdrant-client` package is required.\n"
        "Install it with:\n\n    pip install qdrant-client>=1.9.0"
    ) from exc

from app.config import settings

logger = logging.getLogger(__name__)

__all__ = ["QdrantVectorStore"]


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #
def _run_in_executor(func, *args, **kwargs):
    """Run blocking Qdrant call in a threadpool."""
    return anyio.to_thread.run_sync(func, *args, **kwargs)


# --------------------------------------------------------------------------- #
# Public class
# --------------------------------------------------------------------------- #
class QdrantVectorStore:
    """Typed façade around Qdrant collections for knowledge & code."""

    _EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None

    def __init__(
        self,
        *,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_prefix: str = "kb",
        vector_size: int | None = None,
    ) -> None:
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key
        self.vector_size = vector_size or settings.qdrant_vector_size

        self.knowledge_collection = f"{collection_prefix}_knowledge"
        self.code_collection = f"{collection_prefix}_code"

        # A single, shared ThreadPool avoids unbounded thread creation.
        if QdrantVectorStore._EXECUTOR is None:
            QdrantVectorStore._EXECUTOR = concurrent.futures.ThreadPoolExecutor(
                max_workers=settings.qdrant_max_workers or 16,
                thread_name_prefix="qdrant",
            )

        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=settings.qdrant_timeout or 30,  # seconds
        )

    # ------------------------------------------------------------------ #
    # Collection bootstrap
    # ------------------------------------------------------------------ #
    async def init_collections(self) -> None:
        """Create the two default collections if they don't yet exist."""
        async def _ensure(name: str):
            try:
                await _run_in_executor(self.client.get_collection, name)
                logger.info("Qdrant collection '%s' exists", name)
            except Exception:
                await _run_in_executor(
                    self.client.create_collection,
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Qdrant collection '%s' created", name)

        await anyio.gather(*[_ensure(self.knowledge_collection), _ensure(self.code_collection)])

    # ------------------------------------------------------------------ #
    # Upserts
    # ------------------------------------------------------------------ #
    async def add_knowledge_entry(
        self,
        *,
        entry_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> bool:
        point = PointStruct(
            id=entry_id,
            vector=embedding,
            payload={
                "content": content[:1000],
                "title": metadata.get("title", ""),
                "source": metadata.get("source", ""),
                "category": metadata.get("category", ""),
                "tags": metadata.get("tags", []),
                "project_id": metadata.get("project_id"),
                "created_at": metadata.get("created_at", datetime.utcnow().isoformat()),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
        result = await _run_in_executor(
            self.client.upsert,
            collection_name=self.knowledge_collection,
            points=[point],
        )
        return result.status == UpdateStatus.COMPLETED  # type: ignore[attr-defined]

    async def add_code_embedding(
        self,
        *,
        chunk_id: int,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> bool:
        point = PointStruct(
            id=str(chunk_id),
            vector=embedding,
            payload={
                "chunk_id": chunk_id,
                "document_id": metadata["document_id"],
                "project_id": metadata["project_id"],
                "file_path": metadata["file_path"],
                "language": metadata.get("language", ""),
                "symbol_name": metadata.get("symbol_name", ""),
                "symbol_type": metadata.get("symbol_type", ""),
                "start_line": metadata.get("start_line", 0),
                "end_line": metadata.get("end_line", 0),
                "content_preview": metadata.get("content", "")[:200],
            },
        )
        result = await _run_in_executor(
            self.client.upsert,
            collection_name=self.code_collection,
            points=[point],
        )
        return result.status == UpdateStatus.COMPLETED  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Searches
    # ------------------------------------------------------------------ #
    async def search_knowledge(
        self,
        *,
        query_embedding: List[float],
        project_ids: Optional[List[int]] = None,
        limit: int = 10,
        score_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        search_filter = self._build_knowledge_filter(project_ids, filters)
        results = await _run_in_executor(
            self.client.search,
            collection_name=self.knowledge_collection,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            score_threshold=score_threshold,
        )
        return [
            {
                "id": p.id,
                "score": p.score,
                **p.payload,
            }
            for p in results
        ]

    async def search_code(
        self,
        *,
        query_embedding: List[float],
        project_ids: Optional[List[int]] = None,
        language: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        search_filter = self._build_code_filter(project_ids, language)
        results = await _run_in_executor(
            self.client.search,
            collection_name=self.code_collection,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            score_threshold=score_threshold,
        )
        return [
            {
                "chunk_id": p.payload.get("chunk_id"),
                "score": p.score,
                **p.payload,
            }
            for p in results
        ]

    # ------------------------------------------------------------------ #
    # Deletion & stats
    # ------------------------------------------------------------------ #
    async def delete_by_project(self, project_id: int, *, collection: str | None = None) -> None:
        collections = [collection] if collection else [self.knowledge_collection, self.code_collection]

        async def _delete(coll: str):
            await _run_in_executor(
                self.client.delete,
                collection_name=coll,
                points_selector=Filter(
                    must=[FieldCondition(key="project_id", match=MatchValue(value=project_id))]
                ),
            )
            logger.info("Deleted project %s from '%s'", project_id, coll)

        await anyio.gather(*[_delete(c) for c in collections])

    async def get_stats(self) -> Dict[str, Any]:
        async def _stats(coll: str):
            try:
                info = await _run_in_executor(self.client.get_collection, coll)
                return coll, {
                    "vectors_count": info.vectors_count,
                    "indexed_vectors_count": info.indexed_vectors_count,
                    "status": info.status,
                }
            except Exception as exc:
                return coll, {"error": str(exc)}

        results = await anyio.gather(
            *_stats(self.knowledge_collection),
            *_stats(self.code_collection),
        )
        return dict(results)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_knowledge_filter(
        project_ids: Optional[List[int]], filters: Optional[Dict[str, Any]]
    ) -> Filter | None:
        must: List[Any] = []
        if project_ids:
            must.append(FieldCondition(key="project_id", match=MatchAny(any=project_ids)))
        if filters:
            if "category" in filters:
                must.append(FieldCondition(key="category", match=MatchValue(value=filters["category"])))
            for tag in filters.get("tags", []):
                must.append(FieldCondition(key="tags", match=MatchValue(value=tag)))
        return Filter(must=must) if must else None

    @staticmethod
    def _build_code_filter(
        project_ids: Optional[List[int]], language: Optional[str]
    ) -> Filter | None:
        must: List[Any] = []
        if project_ids:
            must.append(FieldCondition(key="project_id", match=MatchAny(any=project_ids)))
        if language:
            must.append(FieldCondition(key="language", match=MatchValue(value=language)))
        return Filter(must=must) if must else None
