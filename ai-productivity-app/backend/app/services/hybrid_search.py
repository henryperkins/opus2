# backend/app/services/hybrid_search.py
"""Unified hybrid search combining vector, keyword, and structural search."""
from typing import List, Dict, Optional
import asyncio
from sqlalchemy.orm import Session
import numpy as np
import logging
import hashlib

from app.services.vector_service import VectorService
from app.services.keyword_search import KeywordSearch
from app.services.structural_search import StructuralSearch
from app.embeddings.generator import EmbeddingGenerator

logger = logging.getLogger(__name__)


class HybridSearch:
    """Unified search across all modalities."""

    def __init__(
        self,
        db: Session,
        vector_service: VectorService,
        embedding_generator: Optional[EmbeddingGenerator] = None,
    ):
        self.db = db
        self.vector_service = vector_service
        self.embedding_generator = embedding_generator
        self.keyword_search = KeywordSearch(db)
        self.structural_search = StructuralSearch(db)

        # Search weights
        self.weights = {"semantic": 0.5, "keyword": 0.3, "structural": 0.2}

    async def search(
        self,
        query: str,
        project_ids: List[int],
        filters: Optional[Dict] = None,
        limit: int = 20,
        search_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Execute hybrid search across all modalities."""
        if not search_types:
            search_types = ["semantic", "keyword", "structural"]

        # Check if structural search applies
        structural_parsed = self.structural_search._parse_query(query)
        if structural_parsed:
            # Prioritize structural search for specific queries
            search_types = ["structural"]

        # Execute searches in parallel
        tasks = []
        if "semantic" in search_types and self.embedding_generator:
            tasks.append(self._semantic_search(query, project_ids, filters, limit))
        if "keyword" in search_types:
            tasks.append(self.keyword_search.search(query, project_ids, filters, limit))
        if "structural" in search_types:
            tasks.append(
                self.structural_search.search(query, project_ids, filters, limit)
            )

        if not tasks:
            return []

        # Wait for all searches
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge results
        all_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Search failed: {result}")
                continue
            all_results.extend(result)

        # Deduplicate and rank
        ranked_results = self._rank_and_dedupe(all_results, limit)

        return ranked_results

    async def _semantic_search(
        self, query: str, project_ids: List[int], filters: Optional[Dict], limit: int
    ) -> List[Dict]:
        """Execute semantic vector search."""
        if not self.embedding_generator:
            return []

        try:
            # Generate query embedding
            query_embedding = await self.embedding_generator.generate_single_embedding(
                query
            )
            if not query_embedding:
                return []

            # Search vector store
            results = await self.vector_service.search(
                query_vector=np.array(query_embedding),
                limit=limit * 2,  # Get more for filtering
                project_ids=project_ids,
            )

            # Apply additional filters
            if filters:
                filtered = []
                for result in results:
                    metadata = result.get("metadata", {})
                    if (
                        filters.get("language")
                        and metadata.get("language") != filters["language"]
                    ):
                        continue
                    if filters.get("file_type") == "test":
                        if "test" not in metadata.get("file_path", "").lower():
                            continue
                    filtered.append(result)
                results = filtered

            # Format results
            formatted = []
            for result in results[:limit]:
                formatted.append(
                    {
                        "type": "semantic",
                        "score": result["score"] * self.weights["semantic"],
                        "document_id": result["document_id"],
                        "chunk_id": result["chunk_id"],
                        "content": result["content"],
                        "metadata": result["metadata"],
                    }
                )

            return formatted

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _rank_and_dedupe(self, results: List[Dict], limit: int) -> List[Dict]:
        """Rank and deduplicate results."""
        # Group by content hash
        grouped = {}
        for result in results:
            # Create content hash for deduplication
            content_hash = hashlib.md5(
                f"{result.get('document_id', 0)}:{result.get('chunk_id', 0)}:{result['content'][:100]}".encode()
            ).hexdigest()

            if content_hash not in grouped:
                grouped[content_hash] = result
            else:
                # Merge scores
                existing = grouped[content_hash]
                existing["score"] = max(existing["score"], result["score"])

                # Merge types
                if existing["type"] != result["type"]:
                    existing["type"] = "hybrid"

        # Sort by score
        ranked = sorted(grouped.values(), key=lambda x: x["score"], reverse=True)

        return ranked[:limit]

    async def get_context_for_query(
        self, query: str, project_ids: List[int], max_tokens: int = 4000
    ) -> str:
        """Get relevant context for LLM prompts."""
        results = await self.search(query, project_ids, limit=10)

        context_parts = []
        current_tokens = 0

        for result in results:
            metadata = result.get("metadata", {})

            # Format context
            context = f"\n# File: {metadata.get('file_path', 'Unknown')}"
            if metadata.get("symbol_name"):
                context += f"\n# {metadata['symbol_type']}: {metadata['symbol_name']}"
            if metadata.get("start_line"):
                context += f" (lines {metadata['start_line']}-{metadata['end_line']})"
            context += f"\n\n{result['content']}\n"

            # Estimate tokens
            estimated_tokens = len(context) // 4
            if current_tokens + estimated_tokens > max_tokens:
                break

            context_parts.append(context)
            current_tokens += estimated_tokens

        return "\n---\n".join(context_parts)
