# backend/app/services/knowledge_service.py
"""Knowledge base service with Qdrant integration."""
import logging
import math
from datetime import datetime
from typing import List, Dict, Any, Optional

# ---------------------------------------------------------------------------
# ``tiktoken`` is an optional dependency used for accurate token counting.  In
# minimal CI environments the wheel might be missing.  We therefore import it
# lazily and fall back to a **very small** stub that provides the limited API
# (`get_encoding`, `encoding_for_model`, `encode`) required by this module so
# that the remainder of the application can still start and the unit tests can
# run without the heavy binary dependency.
# ---------------------------------------------------------------------------

try:
    import tiktoken  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – lightweight fallback for CI

    class _EncodingStub:  # pylint: disable=too-few-public-methods
        """Extremely simplified tokenizer replacement."""

        def encode(self, text: str):  # noqa: D401 – mimic tiktoken API
            # More conservative token estimation: ~4 chars per token with safety factor
            # This helps avoid context overflows when tiktoken is not available
            estimated_tokens = max(1, len(text) // 3)  # Conservative 3 chars/token
            return list(range(estimated_tokens))  # Return dummy tokens for counting

        def decode(self, tokens):  # noqa: D401 – mimic tiktoken API
            # For fallback mode with dummy tokens, approximate text reconstruction
            # Since we can't truly decode, return truncated version of text
            if isinstance(tokens, list):
                # Estimate ~3 chars per token and reconstruct placeholder text
                return "..." + " [truncated]"
            return str(tokens)

    class _TiktokenStub:  # pylint: disable=too-few-public-methods
        """Minimal subset of the tiktoken public interface."""

        _enc = _EncodingStub()

        @staticmethod
        def get_encoding(_name: str):  # noqa: D401
            return _TiktokenStub._enc

        @staticmethod
        def encoding_for_model(_model: str):  # noqa: D401
            return _TiktokenStub._enc

    tiktoken = _TiktokenStub()  # type: ignore
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.vector_store.qdrant_client import QdrantVectorStore
from app.embeddings.generator import EmbeddingGenerator
from app.models.knowledge import KnowledgeDocument
from app.config import settings

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

        # Context building parameters
        self.context_alpha = getattr(settings, 'knowledge_context_alpha', 0.7)  # similarity weight
        self.context_beta = getattr(settings, 'knowledge_context_beta', 0.3)   # recency weight

    async def add_knowledge_entry(
        self,
        content: str,
        title: str,
        source: str,
        category: str,
        tags: List[str],
        project_id: int,
        db: Session = None
    ) -> str:
        """Add entry to knowledge base."""
        # Generate embedding
        embedding = await self.embedding_generator.generate_single_embedding(
            content
        )

        # Create entry ID
        entry_id = f"kb_{project_id}_{hash(content)}"

        # First, persist full document to database
        if db:
            knowledge_doc = KnowledgeDocument(
                id=entry_id,
                project_id=project_id,
                content=content,
                title=title,
                source=source,
                category=category
            )
            db.add(knowledge_doc)
            db.commit()
            logger.info(f"Persisted knowledge document to database: {entry_id}")

        # Store preview in vector database with schema version
        preview_content = content[:1000]  # Store only preview in vector store
        success = await self.vector_store.add_knowledge_entry(
            entry_id=entry_id,
            content=preview_content,
            embedding=embedding,
            metadata={
                "title": title,
                "source": source,
                "category": category,
                "tags": tags,
                "project_id": project_id,
                "schema_version": 1  # Track schema version for future migrations
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
        similarity_threshold: float = 0.5,
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
            score_threshold=similarity_threshold,
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
        max_context_length: int = 4000,
        model_name: str = "gpt-4",
        db: Session = None,
        search_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Build production-grade context from knowledge entries with token limits and citations."""
        if not entry_ids or not db:
            return {
                "context": "",
                "citations": {},
                "context_length": 0
            }

        # Get tokenizer for accurate token counting
        try:
            enc = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to a common encoding if model not found
            enc = tiktoken.get_encoding("cl100k_base")

        # Fetch full knowledge documents from database
        # Handle both sync and async sessions
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.id.in_(entry_ids))
        
        # Check if db is async or sync session
        if hasattr(db, 'execute') and hasattr(db, 'commit') and not hasattr(db.__class__, '__aenter__'):
            # Sync session - execute without await
            result = db.execute(stmt)
            documents = result.scalars().all()
        else:
            # Async session - execute with await
            result = await db.execute(stmt)
            documents = result.scalars().all()

        if not documents:
            return {
                "context": "",
                "citations": {},
                "context_length": 0
            }

        # Create lookup for search result metadata
        search_lookup = {}
        if search_results:
            for result in search_results:
                search_lookup[result.get('id')] = result

        # Rank entries by similarity + recency
        ranked_entries = self._rank_entries(documents, entry_ids)

        # Build context with token limits
        context_parts = []
        citation_map = {}
        tokens_used = 0

        for idx, doc in enumerate(ranked_entries):
            # Create citation marker
            marker = f"[{idx + 1}]"

            # Prepare content with citation
            content_with_citation = f"{marker} {doc.content}"

            # Count tokens for this entry
            entry_tokens = len(enc.encode(content_with_citation))

            # Check if adding this entry would exceed limit
            if tokens_used + entry_tokens > max_context_length:
                # Try to fit a truncated version
                remaining_tokens = max_context_length - tokens_used
                if remaining_tokens > 100:  # Only truncate if we have reasonable space
                    # Truncate content to fit
                    truncated_content = self._truncate_to_tokens(
                        doc.content, remaining_tokens - 10, enc  # -10 for marker and spacing
                    )
                    content_with_citation = f"{marker} {truncated_content}..."
                    context_parts.append(content_with_citation)
                    
                    # Update tokens_used with actual truncated size
                    tokens_used += len(enc.encode(content_with_citation))

                    # Add to citation map with search metadata
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

            # Add full content
            context_parts.append(content_with_citation)
            tokens_used += entry_tokens

            # Add to citation map with search metadata
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
        final_tokens = len(enc.encode(final_context))

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
