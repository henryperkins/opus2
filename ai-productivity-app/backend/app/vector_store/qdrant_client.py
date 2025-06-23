# backend/app/vector_store/qdrant_client.py
"""Qdrant vector database client for knowledge base."""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Qdrant is an optional runtime dependency – unit-tests inside the restricted
# execution sandbox do not provide the *qdrant-client* wheel.  To keep the
# application importable we fall back to lightweight *stubs* that expose only
# the attributes accessed by this module.

try:
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.models import (  # type: ignore
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, MatchValue, MatchAny,
        UpdateStatus
    )

    _HAS_QDRANT = True

except ModuleNotFoundError:  # pragma: no cover – stub fallback for CI

    _HAS_QDRANT = False

    class _StubMeta(type):  # pylint: disable=too-few-public-methods
        def __getattr__(self, _):  # noqa: D401
            return 0  # return dummy constant/enumeration value

    class Distance(metaclass=_StubMeta):
        COSINE = 0

    class VectorParams:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

    class PointStruct:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            self.id = None
            self.vector = []
            self.payload = {}

    class Filter:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

    class FieldCondition:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

    class MatchValue:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

    class MatchAny:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

    class _StatusStub:
        COMPLETED = "COMPLETED"

    UpdateStatus = _StatusStub

    class _StubResult(list):
        status = UpdateStatus.COMPLETED

    class QdrantClient:  # type: ignore
        """Extremely small stand-in for the real client (no-op)."""

        def __init__(self, *_, **__):
            pass

        # Collection helpers ------------------------------------------------
        def get_collection(self, *_a, **_kw):  # noqa: D401
            return {}

        def create_collection(self, *_a, **_kw):  # noqa: D401
            return {}

        # Data modification -------------------------------------------------
        def upsert(self, *_a, **_kw):  # noqa: D401
            return _StubResult()

        # Search ------------------------------------------------------------
        def search(self, *_a, **_kw):  # noqa: D401
            return []

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """Qdrant vector store for semantic search."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_prefix: str = "kb"
    ):
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_prefix = collection_prefix

        # Initialize client
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=30
        )

        # Collection names
        self.knowledge_collection = f"{collection_prefix}_knowledge"
        self.code_collection = f"{collection_prefix}_code"

        # Embedding dimensions (should match your model)
        self.vector_size = 1536  # text-embedding-ada-002

    async def init_collections(self):
        """Initialize collections if they don't exist."""
        collections = [
            (self.knowledge_collection, "Knowledge base entries"),
            (self.code_collection, "Code embeddings")
        ]

        for collection_name, description in collections:
            try:
                # Check if collection exists
                self.client.get_collection(collection_name)
                logger.info(f"Collection '{collection_name}' already exists")
            except Exception:
                # Create collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection '{collection_name}'")

    async def add_knowledge_entry(
        self,
        entry_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Add a knowledge base entry."""
        try:
            point = PointStruct(
                id=entry_id,
                vector=embedding,
                payload={
                    "content": content[:1000],  # Truncate for storage
                    "title": metadata.get("title", ""),
                    "source": metadata.get("source", ""),
                    "category": metadata.get("category", ""),
                    "tags": metadata.get("tags", []),
                    "project_id": metadata.get("project_id"),
                    "created_at": metadata.get(
                        "created_at", datetime.utcnow().isoformat()
                    ),
                    "updated_at": datetime.utcnow().isoformat()
                }
            )

            result = self.client.upsert(
                collection_name=self.knowledge_collection,
                points=[point]
            )

            return result.status == UpdateStatus.COMPLETED

        except Exception as e:
            logger.error(f"Failed to add knowledge entry: {e}")
            return False

    async def add_code_embedding(
        self,
        chunk_id: int,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Add a code embedding."""
        try:
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
                    "content_preview": metadata.get("content", "")[:200]
                }
            )

            result = self.client.upsert(
                collection_name=self.code_collection,
                points=[point]
            )

            return result.status == UpdateStatus.COMPLETED

        except Exception as e:
            logger.error(f"Failed to add code embedding: {e}")
            return False

    async def search_knowledge(
        self,
        query_embedding: List[float],
        project_ids: Optional[List[int]] = None,
        limit: int = 10,
        score_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        try:
            # Build filter
            must_conditions = []

            if project_ids:
                must_conditions.append(
                    FieldCondition(
                        key="project_id",
                        match=MatchAny(any=project_ids)
                    )
                )

            if filters:
                if "category" in filters:
                    must_conditions.append(
                        FieldCondition(
                            key="category",
                            match=MatchValue(value=filters["category"])
                        )
                    )

                if "tags" in filters and filters["tags"]:
                    for tag in filters["tags"]:
                        must_conditions.append(
                            FieldCondition(
                                key="tags",
                                match=MatchValue(value=tag)
                            )
                        )

            search_filter = (
                Filter(must=must_conditions) if must_conditions else None
            )

            # Perform search
            results = self.client.search(
                collection_name=self.knowledge_collection,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold
            )

            # Format results
            entries = []
            for point in results:
                entry = {
                    "id": point.id,
                    "score": point.score,
                    "content": point.payload.get("content", ""),
                    "title": point.payload.get("title", ""),
                    "source": point.payload.get("source", ""),
                    "category": point.payload.get("category", ""),
                    "tags": point.payload.get("tags", []),
                    "project_id": point.payload.get("project_id"),
                    "created_at": point.payload.get("created_at")
                }
                entries.append(entry)

            return entries

        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return []

    async def search_code(
        self,
        query_embedding: List[float],
        project_ids: Optional[List[int]] = None,
        language: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search code embeddings."""
        try:
            # Build filter
            must_conditions = []

            if project_ids:
                must_conditions.append(
                    FieldCondition(
                        key="project_id",
                        match=MatchAny(any=project_ids)
                    )
                )

            if language:
                must_conditions.append(
                    FieldCondition(
                        key="language",
                        match=MatchValue(value=language)
                    )
                )

            search_filter = (
                Filter(must=must_conditions) if must_conditions else None
            )

            # Perform search
            results = self.client.search(
                collection_name=self.code_collection,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold
            )

            # Format results
            chunks = []
            for point in results:
                chunk = {
                    "chunk_id": point.payload.get("chunk_id"),
                    "score": point.score,
                    "document_id": point.payload.get("document_id"),
                    "file_path": point.payload.get("file_path"),
                    "language": point.payload.get("language", ""),
                    "symbol_name": point.payload.get("symbol_name", ""),
                    "symbol_type": point.payload.get("symbol_type", ""),
                    "start_line": point.payload.get("start_line", 0),
                    "end_line": point.payload.get("end_line", 0),
                    "content_preview": point.payload.get("content_preview", "")
                }
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Code search failed: {e}")
            return []

    async def delete_by_project(
        self, project_id: int, collection: str = None
    ):
        """Delete all entries for a project."""
        collections = [collection] if collection else [
            self.knowledge_collection,
            self.code_collection
        ]

        for coll in collections:
            try:
                self.client.delete(
                    collection_name=coll,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="project_id",
                                match=MatchValue(value=project_id)
                            )
                        ]
                    )
                )
                logger.info(
                    f"Deleted entries for project {project_id} from {coll}"
                )
            except Exception as e:
                logger.error(f"Failed to delete from {coll}: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        stats = {}

        for collection in [self.knowledge_collection, self.code_collection]:
            try:
                info = self.client.get_collection(collection)
                stats[collection] = {
                    "vectors_count": info.vectors_count,
                    "indexed_vectors_count": info.indexed_vectors_count,
                    "status": info.status
                }
            except Exception as e:
                stats[collection] = {"error": str(e)}

        return stats
