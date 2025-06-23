# backend/app/services/qdrant_service.py
"""Qdrant vector database service for semantic search."""
from typing import List, Dict, Optional, Any
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import logging

logger = logging.getLogger(__name__)


class QdrantService:
    """Qdrant vector database service for embeddings."""

    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "kb_entries"

    async def initialize(self) -> None:
        """Initialize the Qdrant service."""
        await self.create_index_if_missing()

    async def create_index_if_missing(self):
        """Ensure the collection exists with proper configuration."""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection with HNSW index
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI embedding dimension
                        distance=Distance.COSINE
                    ),
                    hnsw_config=models.HnswConfigDiff(
                        m=16,  # Number of bi-directional links
                        ef_construct=200,  # Size of dynamic candidate list
                    )
                )
                logger.info(
                    f"Created Qdrant collection: {self.collection_name}"
                )
            else:
                logger.info(
                    f"Qdrant collection already exists: {self.collection_name}"
                )

        except Exception as e:
            logger.error(f"Failed to create Qdrant collection: {e}")
            raise

    async def upsert(self, embeddings: List[Dict[str, Any]]) -> List[str]:
        """Insert or update embeddings in Qdrant."""
        points = []

        for embedding_data in embeddings:
            # Convert vector to list format
            vector_data = embedding_data["vector"]
            if isinstance(vector_data, np.ndarray):
                vector_list = vector_data.tolist()
            else:
                vector_list = vector_data

            point = PointStruct(
                id=embedding_data["id"],
                vector=vector_list,
                payload={
                    "document_id": embedding_data.get("document_id"),
                    "project_id": embedding_data.get("project_id"),
                    "content": embedding_data.get("content", ""),
                    "chunk_id": embedding_data.get("chunk_id"),
                    "metadata": embedding_data.get("metadata", {})
                }
            )
            points.append(point)

        # Upsert points
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        return [str(p.id) for p in points]

    async def search(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        project_ids: Optional[List[int]] = None,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        # Build filter conditions
        filters = []
        if project_ids:
            filters.append(
                models.FieldCondition(
                    key="project_id",
                    match=models.MatchAny(any=project_ids)
                )
            )

        query_filter = models.Filter(must=filters) if filters else None

        # Convert query vector to list format
        if isinstance(query_vector, np.ndarray):
            query_vector_list = query_vector.tolist()
        else:
            query_vector_list = query_vector

        # Perform search
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector_list,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold
        )

        # Format results
        results = []
        for result in search_results:
            results.append({
                "id": result.id,
                "score": result.score,
                "document_id": result.payload.get("document_id"),
                "project_id": result.payload.get("project_id"),
                "content": result.payload.get("content", ""),
                "chunk_id": result.payload.get("chunk_id"),
                "metadata": result.payload.get("metadata", {})
            })

        return results

    async def delete_by_document(self, document_id: int):
        """Delete all vectors for a document."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                )
            )
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        info = self.client.get_collection(self.collection_name)
        return {
            "total_points": info.points_count,
            "vector_size": info.config.params.vectors.size,
            "distance_metric": info.config.params.vectors.distance,
            "collection_name": self.collection_name
        }
