# backend/app/services/knowledge_service.py
"""Knowledge base service with Qdrant integration."""
import logging
from typing import List, Dict, Any, Optional

from app.vector_store.qdrant_client import QdrantVectorStore
from app.embeddings.generator import EmbeddingGenerator

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service for knowledge base operations."""

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        embedding_generator: EmbeddingGenerator
    ):
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator

    async def add_knowledge_entry(
        self,
        content: str,
        title: str,
        source: str,
        category: str,
        tags: List[str],
        project_id: int
    ) -> str:
        """Add entry to knowledge base."""
        # Generate embedding
        embedding = await self.embedding_generator.generate_single_embedding(
            content
        )

        # Create entry ID
        entry_id = f"kb_{project_id}_{hash(content)}"

        # Store in vector database
        success = await self.vector_store.add_knowledge_entry(
            entry_id=entry_id,
            content=content,
            embedding=embedding,
            metadata={
                "title": title,
                "source": source,
                "category": category,
                "tags": tags,
                "project_id": project_id
            }
        )

        if success:
            logger.info(f"Added knowledge entry: {entry_id}")
            return entry_id
        else:
            raise Exception("Failed to add knowledge entry")

    async def search_knowledge(
        self,
        query: str,
        project_ids: Optional[List[int]] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        # Generate query embedding
        query_embedding = await (
            self.embedding_generator.generate_single_embedding(query)
        )

        # Search vector store
        results = await self.vector_store.search_knowledge(
            query_embedding=query_embedding,
            project_ids=project_ids,
            limit=limit,
            score_threshold=0.5,
            filters=filters
        )

        return results

    async def search_code(
        self,
        query: str,
        project_ids: Optional[List[int]] = None,
        language: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search code embeddings."""
        # Generate query embedding
        query_embedding = await (
            self.embedding_generator.generate_single_embedding(query)
        )

        # Search code vector store
        results = await self.vector_store.search_code(
            query_embedding=query_embedding,
            project_ids=project_ids,
            language=language,
            limit=limit,
            score_threshold=0.5
        )

        return results

    async def build_context(
        self,
        entry_ids: List[str],
        max_length: int = 4000
    ) -> Dict[str, Any]:
        """Build context from knowledge entries."""
        # In real implementation, fetch full entries from database
        # For now, we'll use simplified context building

        context_parts = []
        total_length = 0

        for entry_id in entry_ids:
            # Simplified content fetch - in production this would
            # fetch from the knowledge base or cache
            entry_content = f"[Knowledge entry {entry_id}]"

            if total_length + len(entry_content) > max_length:
                break

            context_parts.append(entry_content)
            total_length += len(entry_content)

        return {
            "context": "\n\n".join(context_parts),
            "sources": entry_ids,
            "context_length": total_length
        }

    async def delete_by_project(self, project_id: int):
        """Delete all entries for a project."""
        await self.vector_store.delete_by_project(project_id)
        logger.info(f"Deleted knowledge entries for project {project_id}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return await self.vector_store.get_stats()
