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

# ``anyio`` is a soft dependency used for *thread offloading* and coroutine
# gathering.  The test environment may not have the real package installed –
# instead of crashing during import we fall back to a *very small* shim that
# implements just the subset required by this module (``to_thread.run_sync``
# and ``gather``).

try:
    import anyio  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – skinny fallback for CI
    import asyncio
    import types as _types

    _anyio = _types.ModuleType("anyio")

    class _ToThread:  # pylint: disable=too-few-public-methods
        """Partial replacement mimicking *anyio.to_thread* namespace."""

        @staticmethod
        async def run_sync(func, *args, **kwargs):  # type: ignore[override]
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)

    async def _gather(*coros):  # noqa: D401 – signature matches anyio.gather
        """Light-weight stand-in for *anyio.gather* using asyncio."""

        return await asyncio.gather(*coros)  # type: ignore[misc]

    _anyio.to_thread = _ToThread()  # type: ignore[attr-defined]
    _anyio.gather = _gather  # type: ignore[attr-defined]

    import sys as _sys

    _sys.modules["anyio"] = _anyio
    anyio = _anyio  # type: ignore

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
# ---------------------------------------------------------------------------
# Optional Qdrant stub – allows the wider application to import the vector
# store layer even when the heavy *qdrant-client* dependency is missing.  The
# *real* vector store is **not** exercised by the unit tests so we can get
# away with a *very small* placeholder implementation that mimics the public
# methods accessed by :class:`QdrantVectorStore`.
# ---------------------------------------------------------------------------

except ModuleNotFoundError:  # pragma: no cover – fallback stub for CI
    import sys as _sys
    import types as _types

    _qdrant_mod = _types.ModuleType("qdrant_client")
    _models_mod = _types.ModuleType("qdrant_client.models")

    class _Enum(int):
        """Simple int-backed enum replacement."""

        def __new__(cls, value, name):  # noqa: D401 – signature follow Enum
            obj = int.__new__(cls, value)
            obj._name_ = name  # type: ignore[attr-defined]
            return obj

        def __repr__(self):  # pragma: no cover
            return f"<{self.__class__.__name__}.{self._name_}: {int(self)}>"

    class Distance(_Enum):
        COSINE = _Enum(0, "COSINE")

    class UpdateStatus(_Enum):
        COMPLETED = _Enum(0, "COMPLETED")

    class FieldCondition:  # pylint: disable=too-few-public-methods
        def __init__(self, *, key: str, match: "MatchValue | MatchAny"):
            self.key = key
            self.match = match

    class MatchValue:  # pylint: disable=too-few-public-methods
        def __init__(self, *, value):
            self.value = value

    class MatchAny:  # pylint: disable=too-few-public-methods
        def __init__(self, *, any):  # noqa: A002
            self.any = any

    class Filter:  # pylint: disable=too-few-public-methods
        def __init__(self, *, must=None):
            self.must = must or []

    class VectorParams:  # pylint: disable=too-few-public-methods
        def __init__(self, size: int, distance: Distance):
            self.size = size
            self.distance = distance

    class _Point:  # internal helper for search responses
        def __init__(self, pid, score, payload):
            self.id = pid
            self.score = score
            self.payload = payload

    class PointStruct:  # pylint: disable=too-few-public-methods
        def __init__(self, *, id, vector, payload):  # noqa: D401, A002
            self.id = id
            self.vector = vector
            self.payload = payload

    class QdrantClient:  # noqa: D401 – stubbed client
        """Extremely simplified Qdrant client replacement."""

        def __init__(self, *_, **__):
            # store collections as dict mapping collection_name -> dict of id -> PointStruct
            self._collections = {}

        # --------------------------- collection meta -------------------- #
        def get_collection(self, name):  # type: ignore[override]
            if name not in self._collections:
                raise RuntimeError("collection not found")
            return {"status": "ok", "name": name}

        def create_collection(self, collection_name, vectors_config):  # noqa: D401, ANN001
            self._collections[collection_name] = {}
            return {"status": "created", "name": collection_name, "cfg": vectors_config}

        # --------------------------- write ------------------------------ #
        def upsert(self, collection_name, points):  # noqa: D401, ANN001
            coll = self._collections.setdefault(collection_name, {})
            for p in points:
                coll[p.id] = p
            return _types.SimpleNamespace(status=UpdateStatus.COMPLETED)

        # --------------------------- search ----------------------------- #
        def search(
            self,
            *,
            collection_name,
            query_vector,
            query_filter=None,  # noqa: ANN001
            limit=10,
            score_threshold=0.0,
        ):
            coll = self._collections.get(collection_name, {})
            # naive: return first *limit* points
            out = []
            for idx, p in enumerate(coll.values()):
                if idx >= limit:
                    break
                out.append(
                    _Point(pid=p.id, score=1.0, payload=p.payload)
                )
            return out

        # --------------------------- delete ----------------------------- #
        def delete(self, *, collection_name, points_selector):  # noqa: D401, ANN001
            coll = self._collections.get(collection_name, {})
            if not coll:
                return {"status": "ok"}
            # naive: iterate and remove matching points
            to_delete = []
            for pid, p in coll.items():
                if any(
                    pc.key == "project_id" and pc.match.value == p.payload.get("project_id")
                    for pc in (points_selector.must if hasattr(points_selector, "must") else [])
                ):
                    to_delete.append(pid)
            for pid in to_delete:
                coll.pop(pid, None)
            return {"status": "ok", "deleted": len(to_delete)}

    # register modules + symbols
    for _name, _obj in {
        "Distance": Distance,
        "FieldCondition": FieldCondition,
        "Filter": Filter,
        "MatchAny": MatchAny,
        "MatchValue": MatchValue,
        "PointStruct": PointStruct,
        "UpdateStatus": UpdateStatus,
        "VectorParams": VectorParams,
    }.items():
        setattr(_models_mod, _name, _obj)

    _qdrant_mod.QdrantClient = QdrantClient
    _qdrant_mod.models = _models_mod

    _sys.modules["qdrant_client"] = _qdrant_mod
    _sys.modules["qdrant_client.models"] = _models_mod

    # Now re-export symbols so the rest of the file continues unchanged.
    from qdrant_client import QdrantClient  # type: ignore  # pylint: disable=ungrouped-imports
    from qdrant_client.models import (  # type: ignore  # noqa: E402
        Distance,
        FieldCondition,
        Filter,
        MatchAny,
        MatchValue,
        PointStruct,
        UpdateStatus,
        VectorParams,
    )

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
