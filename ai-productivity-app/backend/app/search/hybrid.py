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
from typing import List, Dict, Optional, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import select, or_

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

        # -----------------------------------------------------------------
        # Step 1 – always run a very inexpensive SQL keyword search.  This is
        #          especially important when no vectors are available.
        # -----------------------------------------------------------------

        keyword_stmt = (
            select(CodeEmbedding)
            .join(CodeDocument, CodeDocument.id == CodeEmbedding.document_id)
            .where(
                CodeDocument.project_id.in_(project_ids),
                or_(CodeEmbedding.chunk_content.ilike(f"%{query}%"), CodeEmbedding.symbol_name.ilike(f"%{query}%")),
            )
            .limit(limit * 3)  # wider net, will be re-ranked later
        )

        keyword_rows = self.db.execute(keyword_stmt).scalars().all()

        results: list[dict] = []
        for r in keyword_rows:
            results.append(
                {
                    "chunk_id": r.id,
                    "content": r.chunk_content[:500],
                    "file_path": r.document.file_path if r.document else None,
                    "language": r.document.language if r.document else None,
                    "symbol": r.symbol_name,
                    "_keyword_score": 1.0,  # constant placeholder – could be tf-idf in future
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
        """Very small cosine-similarity search directly against SQLite JSON.

        … **not** something you would ever do in production 😉  but more than
        good enough for test-drives and demos without external services.
        """

        from app.models.code import CodeEmbedding, CodeDocument  # late import

        # Load *all* candidate embeddings into memory.  For a typical demo-
        # sized database this is perfectly fine; for anything real this would
        # obviously need a proper vector index.

        stmt = (
            select(CodeEmbedding)
            .join(CodeDocument, CodeDocument.id == CodeEmbedding.document_id)
            .where(CodeDocument.project_id.in_(project_ids), CodeEmbedding.embedding.is_not(None))
        )

        rows = self.db.execute(stmt).scalars().all()

        semantic_results: list[dict] = []

        if not rows:
            return semantic_results

        # Pre-compute norm of query vector once.
        qvec = query_vec

        for r in rows:
            try:
                vec_list = r.embedding  # stored as JSON array
                if not vec_list:
                    continue

                vec = np.asarray(vec_list, dtype=float)
                if vec.shape != qvec.shape:
                    # Skip vectors with wrong dimensionality – could happen
                    # when different embedding models were used.
                    continue

                sim = float(np.dot(qvec, _normalise(vec)))  # cosine similarity (vectors already unit-normed)

                semantic_results.append(
                    {
                        "chunk_id": r.id,
                        "content": r.chunk_content[:500],
                        "file_path": r.document.file_path if r.document else None,
                        "language": r.document.language if r.document else None,
                        "symbol": r.symbol_name,
                        "_semantic_score": sim,
                        "search_type": "semantic",
                    }
                )
            except Exception:  # pragma: no cover – ignore broken rows
                continue

        # Return top-N most similar
        semantic_results.sort(key=lambda x: x["_semantic_score"], reverse=True)

        return semantic_results[:limit]
