# backend/app/services/keyword_search.py
"""Keyword search implementation with PostgreSQL FTS and SQLite FTS5 fallback."""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_, func, text
import re
import logging

from app.models.code import CodeDocument, CodeEmbedding
from app.models.embedding import EmbeddingMetadata

logger = logging.getLogger(__name__)


class KeywordSearch:
    """Full-text and keyword search implementation."""

    def __init__(self, db: Session):
        self.db = db
        self.is_postgresql = db.bind.dialect.name == 'postgresql'

    async def search(
        self,
        query: str,
        project_ids: List[int],
        filters: Optional[Dict] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Perform keyword search using FTS5 and fallback methods."""
        results = []

        # Try PostgreSQL FTS or SQLite FTS5 search first
        try:
            if self.is_postgresql:
                results.extend(await self._postgresql_fts_search(query, project_ids, filters, limit))
            else:
                results.extend(await self._fts_search(query, project_ids, filters, limit))
        except Exception as e:
            logger.warning(f"Full-text search failed: {e}")
            # Reset broken connection state so that subsequent LIKE queries
            # run in the *same* request do not inherit PostgreSQL’s aborted
            # transaction state.
            try:
                if self.db.in_transaction():
                    self.db.rollback()
            except Exception as rollback_exc:  # noqa: BLE001 – best-effort
                logger.error(
                    "Failed to roll back DB session after search error: %s",
                    rollback_exc,
                )

        # Fallback to LIKE search
        if len(results) < limit:
            remaining = limit - len(results)
            results.extend(
                await self._like_search(query, project_ids, filters, remaining)
            )

        # Deduplicate
        seen = set()
        unique_results = []
        for result in results:
            key = f"{result['document_id']}:{result.get('chunk_id', 0)}"
            if key not in seen:
                seen.add(key)
                unique_results.append(result)

        return unique_results[:limit]

    async def _postgresql_fts_search(
        self, query: str, project_ids: List[int], filters: Optional[Dict], limit: int
    ) -> List[Dict]:
        """PostgreSQL full-text search with ranking."""
        # Prepare query for PostgreSQL FTS
        pg_query = self._prepare_postgresql_query(query)
        
        # Search across multiple content types
        sql = text("""
            SELECT 
                m.rowid,
                m.document_id,
                m.chunk_id,
                m.project_id,
                m.content,
                m.metadata,
                ts_rank(to_tsvector('ai_english', m.content), plainto_tsquery('ai_english', :query)) as rank
            FROM embedding_metadata m
            WHERE to_tsvector('ai_english', m.content) @@ plainto_tsquery('ai_english', :query)
                AND m.project_id = ANY(:project_ids)
            ORDER BY rank DESC, m.created_at DESC
            LIMIT :limit
        """)
        
        result = self.db.execute(sql, {
            'query': pg_query,
            'project_ids': project_ids,
            'limit': limit
        })
        
        return [
            {
                'rowid': row.rowid,
                'document_id': row.document_id,
                'chunk_id': row.chunk_id,
                'project_id': row.project_id,
                'content': row.content,
                'metadata': row.metadata,
                'score': float(row.rank),
                'search_type': 'postgresql_fts'
            }
            for row in result
        ]

    async def _fts_search(
        self, query: str, project_ids: List[int], filters: Optional[Dict], limit: int
    ) -> List[Dict]:
        """SQLite FTS5 full-text search."""
        # Escape FTS5 special characters
        fts_query = self._prepare_fts_query(query)

        # Raw SQL for FTS5
        sql = """
            SELECT
                m.rowid,
                m.document_id,
                m.chunk_id,
                m.project_id,
                m.content,
                m.metadata,
                bm25(content_fts) as rank
            FROM content_fts f
            JOIN embedding_metadata m ON f.rowid = m.rowid
            WHERE content_fts MATCH ?
                AND m.project_id IN ({})
            ORDER BY rank
            LIMIT ?
        """.format(
            ",".join(str(p) for p in project_ids)
        )

        result = self.db.execute(sql, [fts_query, limit])

        results = []
        for row in result:
            results.append(
                {
                    "type": "keyword_fts",
                    "score": float(abs(row.rank)),  # BM25 is negative
                    "document_id": row.document_id,
                    "chunk_id": row.chunk_id,
                    "content": row.content,
                    "metadata": row.metadata,
                }
            )

        return results

    async def _like_search(
        self, query: str, project_ids: List[int], filters: Optional[Dict], limit: int
    ) -> List[Dict]:
        """Fallback LIKE search."""
        # Build query
        stmt = (
            select(CodeEmbedding)
            .join(CodeDocument)
            .where(
                CodeDocument.project_id.in_(project_ids),
                or_(
                    CodeEmbedding.chunk_content.ilike(f"%{query}%"),
                    CodeEmbedding.symbol_name.ilike(f"%{query}%"),
                    CodeDocument.file_path.ilike(f"%{query}%"),
                ),
            )
        )

        # Apply filters
        if filters:
            if filters.get("language"):
                stmt = stmt.where(CodeDocument.language == filters["language"])
            if filters.get("file_type"):
                if filters["file_type"] == "test":
                    stmt = stmt.where(
                        or_(
                            CodeDocument.file_path.like("%test%"),
                            CodeDocument.file_path.like("%spec%"),
                        )
                    )

        stmt = stmt.limit(limit)

        results = []
        for chunk in self.db.execute(stmt).scalars():
            # Calculate relevance score
            score = 0.5  # Base score
            query_lower = query.lower()

            # Boost for exact matches
            if query_lower in chunk.chunk_content.lower():
                score += 0.3
            if chunk.symbol_name and query_lower in chunk.symbol_name.lower():
                score += 0.2

            results.append(
                {
                    "type": "keyword_like",
                    "score": score,
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "content": chunk.chunk_content,
                    "metadata": {
                        "symbol_name": chunk.symbol_name,
                        "symbol_type": chunk.symbol_type,
                        "file_path": chunk.document.file_path,
                        "language": chunk.document.language,
                    },
                }
            )

        return results

    def _prepare_fts_query(self, query: str) -> str:
        """Prepare query for SQLite FTS5."""
        # Remove special characters
        query = re.sub(r"[^\w\s]", " ", query)

        # Convert to FTS5 prefix search
        terms = query.split()
        fts_terms = [f'"{term}"*' for term in terms if term]

        return " ".join(fts_terms)
    
    def _prepare_postgresql_query(self, query: str) -> str:
        """Prepare query for PostgreSQL full-text search."""
        # Clean query for PostgreSQL FTS
        query = re.sub(r"[^\w\s]", " ", query)
        
        # Remove extra whitespace
        query = " ".join(query.split())
        
        return query
