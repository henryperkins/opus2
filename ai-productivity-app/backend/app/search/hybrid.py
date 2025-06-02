"""Light-weight *hybrid* search helper used by multiple parts of the code-base.

The original design called for a vector-DB backed implementation (e.g. 
FAISS, Qdrant, Weaviate, …) combined with a traditional SQL / keyword
fallback.  Shipping and compiling those native dependencies in the test
environment however isn’t possible.

This module therefore provides *just enough* functionality for the rest of
the backend to import and use it **without** introducing heavy optional
requirements:

• If embedding vectors exist in the local SQLite database *and* an
  ``EmbeddingGenerator`` instance is provided, we compute the query-embedding
  on-the-fly and perform an **in-process cosine-similarity search** across
  the stored vectors with pure-Python / NumPy.

• If no vectors are available – or NumPy itself is missing – the search
  automatically falls back to a very small SQL *ILIKE* keyword search that
  already existed inside the ``/api/search`` router.

The public API purposefully mirrors what external callers already expect so
that swapping in a “real” vector store in the future will be trivial.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import List, Dict, Optional, Sequence
import math

from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func

# NumPy is an optional dependency – guard the import gracefully so the module
# can still be imported in minimal environments without it.
try:
    import numpy as np

    _HAS_NUMPY = True
except Exception:  # pragma: no cover – NumPy not available
    _HAS_NUMPY = False


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _normalise(v: "np.ndarray") -> "np.ndarray":
    """Return a *unit-length* copy of the supplied 1-D vector."""

    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def _tokenize_query(query: str) -> List[str]:
    """Tokenize query into words for keyword scoring."""
    # Remove special characters and convert to lowercase
    clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
    return [token for token in clean_query.split() if len(token) > 1]


def _calculate_tf_idf_score(content: str, query_tokens: List[str], total_docs: int, term_doc_freq: Dict[str, int]) -> float:
    """Calculate TF-IDF score for content against query tokens."""
    if not query_tokens:
        return 0.0
    
    content_lower = content.lower()
    content_tokens = _tokenize_query(content_lower)
    
    if not content_tokens:
        return 0.0
    
    # Calculate term frequency in document
    content_counter = Counter(content_tokens)
    doc_length = len(content_tokens)
    
    score = 0.0
    for token in query_tokens:
        tf = content_counter.get(token, 0) / doc_length if doc_length > 0 else 0
        
        if tf > 0:
            # Calculate IDF
            doc_freq = term_doc_freq.get(token, 1)
            idf = math.log(total_docs / doc_freq) if doc_freq > 0 else 0
            score += tf * idf
    
    return score


def _expand_query(query: str) -> List[str]:
    """Expand query with related terms (simple implementation)."""
    query_tokens = _tokenize_query(query)
    expanded = set(query_tokens)
    
    # Add programming-specific expansions
    programming_expansions = {
        'function': ['func', 'method', 'def'],
        'class': ['cls', 'object', 'type'],
        'variable': ['var', 'param', 'arg'],
        'import': ['include', 'require', 'from'],
        'return': ['ret', 'yield'],
        'error': ['exception', 'fail', 'bug'],
        'test': ['spec', 'unit', 'assert'],
        'config': ['configuration', 'settings', 'options'],
        'data': ['info', 'content', 'value'],
        'api': ['endpoint', 'service', 'interface'],
    }
    
    for token in query_tokens:
        if token in programming_expansions:
            expanded.update(programming_expansions[token])
    
    return list(expanded)


# ---------------------------------------------------------------------------
# Hybrid search implementation
# ---------------------------------------------------------------------------


class HybridSearch:
    """Perform a combined embedding + keyword search over *code chunks*.

    Parameters
    ----------
    db:
        SQLAlchemy session connected to the application database.
    embedding_generator:
        Optional async generator that can compute an embedding for a single
        query string.  If *None*, purely keyword based search is used.
    """

    def __init__(self, db: Session, embedding_generator: Optional[object] = None):
        self.db = db
        self.embedding_generator = embedding_generator

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        project_ids: Sequence[int] | None = None,
        limit: int = 20,
        alpha: float = 0.5,
    ) -> List[Dict]:
        """Return *up to* ``limit`` results ordered by a blended score.

        The returned dictionaries are intentionally *schema-less*; the search
        router converts them to JSON directly.  Each dictionary therefore at
        least contains:

        • ``chunk_id`` – primary key of the ``CodeEmbedding`` row.
        • ``content`` – snippet preview (truncated).
        • ``file_path`` – originating file.
        • ``language`` – programming language.
        • ``symbol`` – symbol name (if any).
        • ``score`` – blended similarity score (higher == better).
        • ``search_type`` – "hybrid" / "semantic" / "keyword".
        """

        from app.models.code import CodeEmbedding, CodeDocument  # local import to prevent circular deps

        if project_ids is None or len(project_ids) == 0:
            # Default to *all* projects
            project_ids = [p for (p,) in self.db.query(CodeDocument.project_id).distinct().all()] or [0]

        # Expand query for better matches
        expanded_terms = _expand_query(query)
        query_tokens = _tokenize_query(query)
        
        # Get total document count for IDF calculation
        total_docs = self.db.query(CodeEmbedding).join(CodeDocument).filter(
            CodeDocument.project_id.in_(project_ids)
        ).count()
        
        # Calculate term document frequencies for IDF
        term_doc_freq = self._calculate_term_frequencies(expanded_terms, project_ids)

        # -----------------------------------------------------------------
        # Step 1 – optimized keyword search with better scoring
        # -----------------------------------------------------------------

        # Build more sophisticated query using expanded terms
        search_conditions = []
        for term in expanded_terms:
            search_conditions.extend([
                CodeEmbedding.chunk_content.ilike(f"%{term}%"),
                CodeEmbedding.symbol_name.ilike(f"%{term}%")
            ])

        keyword_stmt = (
            select(CodeEmbedding)
            .join(CodeDocument, CodeDocument.id == CodeEmbedding.document_id)
            .where(
                CodeDocument.project_id.in_(project_ids),
                or_(*search_conditions) if search_conditions else CodeEmbedding.chunk_content.ilike(f"%{query}%")
            )
            .limit(limit * 3)  # wider net, will be re-ranked later
        )

        keyword_rows = self.db.execute(keyword_stmt).scalars().all()

        results: list[dict] = []
        for r in keyword_rows:
            # Calculate TF-IDF score instead of constant 1.0
            tf_idf_score = _calculate_tf_idf_score(
                r.chunk_content + " " + (r.symbol_name or ""), 
                query_tokens, 
                total_docs, 
                term_doc_freq
            )
            
            # Boost score for symbol name matches
            symbol_boost = 1.5 if r.symbol_name and any(token in r.symbol_name.lower() for token in query_tokens) else 1.0
            
            results.append(
                {
                    "chunk_id": r.id,
                    "content": r.chunk_content[:500],
                    "file_path": r.document.file_path if r.document else None,
                    "language": r.document.language if r.document else None,
                    "symbol": r.symbol_name,
                    "_keyword_score": tf_idf_score * symbol_boost,
                    "search_type": "keyword",
                }
            )

        # -----------------------------------------------------------------
        # Step 2 – optional *semantic* component.
        # -----------------------------------------------------------------

        semantic_results: list[dict] = []

        if _HAS_NUMPY and self.embedding_generator is not None:
            try:
                # Generate query embedding (embedding_generator may be *async*)
                query_embedding = await self._generate_query_embedding(query)

                if query_embedding is not None:
                    semantic_results = self._semantic_search(query_embedding, project_ids, limit * 3)
            except Exception as exc:  # pragma: no cover – non-critical
                logger.warning("Fallback to keyword search – semantic component failed: %s", exc)

        # Merge & re-rank ---------------------------------------------------

        results.extend(semantic_results)

        # Compute blended score – when semantic component is absent we just
        # rely on the placeholder keyword score of *1.0* so ordering is
        # stable.
        for item in results:
            kw_score = item.get("_keyword_score", 0.0)
            sem_score = item.get("_semantic_score", 0.0)
            item["score"] = (alpha * sem_score) + ((1 - alpha) * kw_score)

        # Deduplicate by *chunk_id* keeping the highest scoring entry.
        dedup: dict[int, dict] = {}
        for item in results:
            cid = item["chunk_id"]
            current = dedup.get(cid)
            if current is None or item["score"] > current["score"]:
                dedup[cid] = item

        # Order by blended score desc and truncate to requested limit.
        ordered: list[dict] = sorted(dedup.values(), key=lambda x: x["score"], reverse=True)[:limit]

        # Clean internal helper keys before returning
        for item in ordered:
            item.pop("_keyword_score", None)
            item.pop("_semantic_score", None)

        # Tag overall search type
        overall_type = "hybrid" if semantic_results else "keyword"
        for item in ordered:
            item["search_type"] = overall_type

        return ordered

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    
    def _calculate_term_frequencies(self, terms: List[str], project_ids: Sequence[int]) -> Dict[str, int]:
        """Calculate document frequency for each term for IDF calculation."""
        from app.models.code import CodeEmbedding, CodeDocument
        
        term_doc_freq = {}
        
        for term in terms:
            # Count documents containing this term
            count = self.db.query(CodeEmbedding).join(CodeDocument).filter(
                CodeDocument.project_id.in_(project_ids),
                or_(
                    CodeEmbedding.chunk_content.ilike(f"%{term}%"),
                    CodeEmbedding.symbol_name.ilike(f"%{term}%")
                )
            ).count()
            
            term_doc_freq[term] = max(count, 1)  # Avoid division by zero
            
        return term_doc_freq

    async def _generate_query_embedding(self, query: str) -> Optional["np.ndarray"]:  # type: ignore[name-defined]
        """Return *unit* vector for the supplied query or *None* on failure."""

        if not _HAS_NUMPY or self.embedding_generator is None:
            return None

        # embedding_generator may expose either *async* or *sync* API – try both
        try:
            emb = None
            if hasattr(self.embedding_generator, "generate_single_embedding"):
                # Our own EmbeddingGenerator happens to be *async* – but
                # calling it synchronously raises a *TypeError* – guard for both
                maybe_coro = self.embedding_generator.generate_single_embedding(query)  # type: ignore[attr-defined]
                if hasattr(maybe_coro, "__await__"):
                    emb = await maybe_coro  # type: ignore[misc]
                else:  # pragma: no cover – unlikely
                    emb = maybe_coro
            else:
                # Assume ``embedding_generator`` itself is *callable*
                maybe_coro = self.embedding_generator(query)  # type: ignore[operator]
                if hasattr(maybe_coro, "__await__"):
                    emb = await maybe_coro  # type: ignore[misc]
                else:  # pragma: no cover
                    emb = maybe_coro

            if emb is None:
                return None

            # Convert to numpy array & normalise
            vec = np.asarray(emb, dtype=float)
            if vec.ndim != 1:
                logger.warning("Query embedding has unexpected shape – expected 1-D, got %s", vec.shape)
                return None

            return _normalise(vec)

        except Exception as exc:  # pragma: no cover
            logger.error("Failed to create query embedding: %s", exc)
            return None

    # ------------------------------------------------------------------
    def _semantic_search(
        self,
        query_vec: "np.ndarray",
        project_ids: Sequence[int],
        limit: int,
    ) -> List[Dict]:
        """Optimized cosine-similarity search with vectorized operations.

        Uses batch processing when NumPy is available for better performance.
        """

        from app.models.code import CodeEmbedding, CodeDocument  # late import

        # Load candidate embeddings into memory with metadata
        stmt = (
            select(CodeEmbedding)
            .join(CodeDocument, CodeDocument.id == CodeEmbedding.document_id)
            .where(CodeDocument.project_id.in_(project_ids), CodeEmbedding.embedding.is_not(None))
        )

        rows = self.db.execute(stmt).scalars().all()

        if not rows:
            return []

        # Try vectorized approach first (faster)
        if _HAS_NUMPY:
            return self._vectorized_semantic_search(query_vec, rows, limit)
        else:
            return self._fallback_semantic_search(query_vec, rows, limit)

    def _vectorized_semantic_search(self, query_vec: "np.ndarray", rows: List, limit: int) -> List[Dict]:
        """Optimized vectorized semantic search using NumPy operations."""
        embeddings = []
        metadata = []
        
        for r in rows:
            try:
                vec_list = r.embedding
                if not vec_list:
                    continue
                    
                vec = np.asarray(vec_list, dtype=float)
                if vec.shape != query_vec.shape:
                    continue
                    
                embeddings.append(_normalise(vec))
                metadata.append(r)
            except Exception:
                continue
        
        if not embeddings:
            return []
            
        # Vectorized cosine similarity computation
        embeddings_matrix = np.stack(embeddings)
        similarities = np.dot(embeddings_matrix, query_vec)
        
        # Get top results
        top_indices = np.argsort(similarities)[::-1][:limit]
        
        semantic_results = []
        for idx in top_indices:
            r = metadata[idx]
            similarity = float(similarities[idx])
            
            semantic_results.append({
                "chunk_id": r.id,
                "content": r.chunk_content[:500],
                "file_path": r.document.file_path if r.document else None,
                "language": r.document.language if r.document else None,
                "symbol": r.symbol_name,
                "_semantic_score": similarity,
                "search_type": "semantic",
            })
            
        return semantic_results

    def _fallback_semantic_search(self, query_vec: "np.ndarray", rows: List, limit: int) -> List[Dict]:
        """Fallback semantic search for when NumPy operations fail."""
        semantic_results = []
        
        for r in rows:
            try:
                vec_list = r.embedding
                if not vec_list:
                    continue

                vec = np.asarray(vec_list, dtype=float)
                if vec.shape != query_vec.shape:
                    continue

                sim = float(np.dot(query_vec, _normalise(vec)))

                semantic_results.append({
                    "chunk_id": r.id,
                    "content": r.chunk_content[:500],
                    "file_path": r.document.file_path if r.document else None,
                    "language": r.document.language if r.document else None,
                    "symbol": r.symbol_name,
                    "_semantic_score": sim,
                    "search_type": "semantic",
                })
            except Exception:
                continue

        # Return top-N most similar
        semantic_results.sort(key=lambda x: x["_semantic_score"], reverse=True)
        return semantic_results[:limit]
