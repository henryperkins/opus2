# backend/app/services/knowledge_service.py
"""Knowledge base service with Qdrant integration."""
import logging
import math
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np

# ---------------------------------------------------------------------------
# ``tiktoken`` is an optional dependency used for accurate token counting.  In
# minimal CI environments the wheel might be missing.  We therefore import it
# lazily and fall back to a **very small** stub that provides the limited API
# (`get_encoding`, `encoding_for_model`, `encode`) required by this module so
# that the remainder of the application can still start and the unit tests can
# run without the heavy binary dependency.
# ---------------------------------------------------------------------------

import tiktoken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.vector_service import VectorService
from app.embeddings.generator import EmbeddingGenerator
from app.models.knowledge import KnowledgeDocument
from app.config import settings

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service for knowledge base operations."""

    def __init__(
        self,
        vector_store: VectorService,
        embedding_generator: EmbeddingGenerator
    ):
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator

        # Context building parameters
        self.context_alpha = getattr(settings, 'knowledge_context_alpha', 0.7)  # similarity weight
        self.context_beta = getattr(settings, 'knowledge_context_beta', 0.3)   # recency weight

    async def add_knowledge_entry(
        self,
        content: str,
        title: str,
        source: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
        project_id: int = 1,
        db: Session = None
    ) -> str:
        """Add entry to knowledge base."""
        if not db:
            raise ValueError("Database session is required")
        
        import uuid
        doc_id = f"kb_{uuid.uuid4().hex[:12]}"
        
        embedding = await self.embedding_generator.generate_single_embedding(content)

        knowledge_doc = KnowledgeDocument(
            id=doc_id,
            project_id=project_id,
            content=content,
            title=title,
            source=source,
            category=category
        )
        
        db.add(knowledge_doc)
        db.commit()
        db.refresh(knowledge_doc)
        logger.info(f"Persisted knowledge document to database: {doc_id}")

        metadata = {
            "title": title,
            "source": source,
            "category": category,
            "project_id": project_id,
            "document_type": "knowledge",
            "knowledge_doc_id": doc_id,
            "tags": tags or [],
            "schema_version": 1
        }
        
        await self.vector_store.insert_embeddings([{
            "id": doc_id,
            "vector": embedding,
            "document_id": knowledge_doc.id,
            "project_id": project_id,
            "content": content,
            "metadata": metadata
        }])
        
        logger.info(f"Added knowledge entry with embedding: {title}")
        return doc_id

    async def search_knowledge(
        self,
        query: str,
        project_ids: Optional[List[int]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
        current_user_id: Optional[int] = None,
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        # Security: Validate project access if current_user_id is provided
        if current_user_id is not None and project_ids and db:
            from app.models.project import Project
            # Verify user owns all requested projects
            user_projects = db.query(Project).filter(
                Project.id.in_(project_ids),
                Project.owner_id == current_user_id
            ).all()
            user_project_ids = [p.id for p in user_projects]
            
            # Only search projects the user actually owns
            project_ids = user_project_ids
            
            if not project_ids:
                # User doesn't own any of the requested projects
                return []
        
        # Generate query embedding
        query_embedding = await (
            self.embedding_generator.generate_single_embedding(query)
        )
        query_vector = np.array(query_embedding)

        # Search vector store
        results = await self.vector_store.search(
            query_vector=query_vector,
            project_ids=project_ids,
            limit=limit,
            score_threshold=similarity_threshold,
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
        query_embedding = await (
            self.embedding_generator.generate_single_embedding(query)
        )
        query_vector = np.array(query_embedding)

        filters = {}
        if language:
            filters["language"] = language

        results = await self.vector_store.search(
            query_vector=query_vector,
            project_ids=project_ids,
            limit=limit,
            score_threshold=0.5,
            filters=filters
        )

        return results

    async def build_context(
        self,
        max_context_length: int = 4000,
        model_name: str = "gpt-4",
        db: Session = None,
        search_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Build production-grade context from knowledge entries with token limits and citations."""
        if not search_results or not db:
            return {
                "context": "",
                "citations": {},
                "context_length": 0
            }

        entry_ids = [result['id'] for result in search_results]
        
        from app.utils.token_counter import get_tokenizer, count_tokens, estimate_max_context_tokens
        enc, is_fallback = get_tokenizer(model_name)

        stmt = select(KnowledgeDocument).where(KnowledgeDocument.id.in_(entry_ids))
        
        if hasattr(db, 'execute') and hasattr(db, 'commit') and not hasattr(db.__class__, '__aenter__'):
            result = db.execute(stmt)
            documents = result.scalars().all()
        else:
            result = await db.execute(stmt)
            documents = result.scalars().all()

        if not documents:
            return {
                "context": "",
                "citations": {},
                "context_length": 0
            }

        search_lookup = {result.get('id'): result for result in search_results}
        ranked_entries = self._rank_entries(documents, entry_ids)

        context_parts = []
        citation_map = {}
        tokens_used = 0

        for idx, doc in enumerate(ranked_entries):
            marker = f"[{idx + 1}]"
            content_with_citation = f"{marker} {doc.content}"
            entry_tokens = count_tokens(content_with_citation, model_name)

            if tokens_used + entry_tokens > max_context_length:
                remaining_tokens = max_context_length - tokens_used
                if remaining_tokens > 100:
                    truncated_content, actual_tokens = estimate_max_context_tokens(
                        doc.content, remaining_tokens - 10, model_name
                    )
                    content_with_citation = f"{marker} {truncated_content}..."
                    context_parts.append(content_with_citation)
                    tokens_used += count_tokens(content_with_citation, model_name)
                    search_data = search_lookup.get(doc.id, {})
                    citation_map[marker] = {
                        "id": doc.id,
                        "title": doc.title,
                        "source": doc.source or "Unknown",
                        "lines": "truncated",
                        "similarity": search_data.get('score', 0.0),
                        "source_type": search_data.get('metadata', {}).get('source_type', 'unknown')
                    }
                break

            context_parts.append(content_with_citation)
            tokens_used += entry_tokens
            search_data = search_lookup.get(doc.id, {})
            citation_map[marker] = {
                "id": doc.id,
                "title": doc.title,
                "source": doc.source or "Unknown",
                "lines": f"1-{len(doc.content.splitlines())}",
                "similarity": search_data.get('score', 0.0),
                "source_type": search_data.get('metadata', {}).get('source_type', 'unknown')
            }

        final_context = "\n\n".join(context_parts)
        final_tokens = count_tokens(final_context, model_name)

        return {
            "context": final_context,
            "citations": citation_map,
            "context_length": final_tokens
        }

    def _rank_entries(self, documents: List[KnowledgeDocument], entry_ids: List[str]) -> List[KnowledgeDocument]:
        """Rank entries by similarity score + recency."""
        # Create a mapping for entry order (similarity score proxy)
        entry_order = {entry_id: idx for idx, entry_id in enumerate(entry_ids)}

        def rank_score(doc):
            # Similarity score (higher index = lower similarity)
            similarity_score = 1.0 - (entry_order.get(doc.id, len(entry_ids)) / len(entry_ids))

            # Recency score (more recent = higher score)
            if doc.created_at and doc.created_at is not None:
                try:
                    now = datetime.utcnow()
                    age_days = (now - doc.created_at).days
                    # Exponential decay with 30-day half-life
                    recency_score = math.exp(-age_days / 30.0)
                except (TypeError, AttributeError):
                    # Fallback for invalid datetime objects
                    recency_score = 0.5
            else:
                recency_score = 0.5  # Default for missing timestamps

            # Weighted combination
            return self.context_alpha * similarity_score + self.context_beta * recency_score

        return sorted(documents, key=rank_score, reverse=True)

    def _truncate_to_tokens(self, text: str, max_tokens: int, encoder) -> str:
        """Truncate text to fit within token limit."""
        tokens = encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text

        # Check if we're using the fallback stub encoder
        if hasattr(encoder, '__class__') and encoder.__class__.__name__ == '_EncodingStub':
            # For fallback mode, do character-based truncation
            # Estimate 3 chars per token as our conservative ratio
            char_limit = max_tokens * 3
            if len(text) <= char_limit:
                return text
            return text[:char_limit].rsplit(' ', 1)[0]  # Truncate at word boundary
        
        # Real tiktoken encoder - truncate tokens and decode back to text
        truncated_tokens = tokens[:max_tokens]
        return encoder.decode(truncated_tokens)

    async def delete_by_project(self, project_id: int):
        """Delete all entries for a project."""
        await self.vector_store.delete_by_project(project_id)
        logger.info(f"Deleted knowledge entries for project {project_id}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return await self.vector_store.get_stats()

