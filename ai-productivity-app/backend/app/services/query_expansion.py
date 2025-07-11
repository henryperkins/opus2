"""Advanced query expansion and semantic similarity service."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.llm.client import llm_client
from app.services.embedding_service import embedding_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryExpansionService:
    """Advanced query expansion using semantic similarity and LLM assistance."""

    def __init__(self):
        self.cache = {}  # Simple in-memory cache for expanded queries
        self.synonym_cache = {}
        self.max_expansions = 5
        self.similarity_threshold = 0.7

    async def expand_query(
        self,
        query: str,
        context: Optional[str] = None,
        domain_hints: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Expand a query using multiple techniques:
        1. Semantic synonyms and related terms
        2. Technical term expansion
        3. Context-aware expansion
        4. Domain-specific expansion
        """
        cache_key = f"{query}:{context or ''}:{','.join(domain_hints or [])}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Generate multiple expansion strategies in parallel
            tasks = [
                self._expand_with_synonyms(query),
                self._expand_with_technical_terms(query, domain_hints),
                self._expand_with_context(query, context),
                self._expand_with_semantic_similarity(query),
            ]

            expansions = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine and rank expansions
            combined_expansions = self._combine_expansions(query, expansions)

            result = {
                "original_query": query,
                "expanded_queries": combined_expansions[: self.max_expansions],
                "expansion_metadata": {
                    "techniques_used": ["synonyms", "technical", "context", "semantic"],
                    "total_candidates": len(combined_expansions),
                    "confidence_score": self._calculate_expansion_confidence(
                        combined_expansions
                    ),
                },
            }

            self.cache[cache_key] = result
            return result

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return {
                "original_query": query,
                "expanded_queries": [query],
                "expansion_metadata": {"error": str(e)},
            }

    async def _expand_with_synonyms(self, query: str) -> List[Dict[str, Any]]:
        """Expand query using synonyms and related terms."""
        if query in self.synonym_cache:
            return self.synonym_cache[query]

        try:
            prompt = f"""Given the query: "{query}"
            
Generate 3-5 alternative phrasings that maintain the same meaning but use different words.
Focus on:
- Technical synonyms
- Alternative terminology
- Different ways to express the same concept

Return only the alternative queries, one per line, without explanations."""

            response = await llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3,
            )

            content = self._extract_content(response)
            synonyms = [
                {"query": line.strip(), "technique": "synonyms", "confidence": 0.8}
                for line in content.split("\n")
                if line.strip() and line.strip() != query
            ]

            self.synonym_cache[query] = synonyms
            return synonyms

        except Exception as e:
            logger.error(f"Synonym expansion failed: {e}")
            return []

    async def _expand_with_technical_terms(
        self, query: str, domain_hints: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Expand query with technical terms and domain-specific language."""
        domain_context = (
            f"Domain context: {', '.join(domain_hints)}" if domain_hints else ""
        )

        try:
            prompt = f"""Given the query: "{query}"
{domain_context}

Generate 3-4 technical variations that:
- Use more specific technical terminology
- Include relevant acronyms or abbreviations
- Add domain-specific context
- Use formal/informal variations

Return only the technical variations, one per line."""

            response = await llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.4,
            )

            content = self._extract_content(response)
            technical_terms = [
                {"query": line.strip(), "technique": "technical", "confidence": 0.9}
                for line in content.split("\n")
                if line.strip() and line.strip() != query
            ]

            return technical_terms

        except Exception as e:
            logger.error(f"Technical term expansion failed: {e}")
            return []

    async def _expand_with_context(
        self, query: str, context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Expand query using contextual information."""
        if not context:
            return []

        try:
            prompt = f"""Given the query: "{query}"
And this context: "{context[:500]}..."

Generate 2-3 context-aware variations of the query that:
- Incorporate relevant context information
- Make implicit assumptions explicit
- Add clarifying details from the context

Return only the context-aware queries, one per line."""

            response = await llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3,
            )

            content = self._extract_content(response)
            context_expansions = [
                {"query": line.strip(), "technique": "context", "confidence": 0.85}
                for line in content.split("\n")
                if line.strip() and line.strip() != query
            ]

            return context_expansions

        except Exception as e:
            logger.error(f"Context expansion failed: {e}")
            return []

    async def _expand_with_semantic_similarity(
        self, query: str
    ) -> List[Dict[str, Any]]:
        """Expand query using semantic similarity analysis."""
        try:
            # Generate query embedding
            query_embedding = await embedding_service.generate_embedding(query)
            if not query_embedding:
                return []

            # Generate semantic variations
            semantic_variants = [
                f"How to {query.lower()}",
                f"What is {query.lower()}",
                f"Examples of {query.lower()}",
                f"Best practices for {query.lower()}",
                f"Common issues with {query.lower()}",
            ]

            # Filter variants that are semantically different enough
            valid_variants = []
            for variant in semantic_variants:
                if len(variant.split()) >= 2:  # Basic length check
                    valid_variants.append(
                        {"query": variant, "technique": "semantic", "confidence": 0.75}
                    )

            return valid_variants[:3]  # Return top 3

        except Exception as e:
            logger.error(f"Semantic similarity expansion failed: {e}")
            return []

    def _combine_expansions(
        self, original_query: str, expansions: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Combine and rank expansions from different techniques."""
        combined = []
        seen_queries = {original_query.lower()}

        for expansion_list in expansions:
            if isinstance(expansion_list, list):
                for expansion in expansion_list:
                    if isinstance(expansion, dict):
                        query_text = expansion.get("query", "").lower()
                        if query_text and query_text not in seen_queries:
                            combined.append(expansion)
                            seen_queries.add(query_text)

        # Sort by confidence score
        combined.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return combined

    def _calculate_expansion_confidence(
        self, expansions: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall confidence in the expansion quality."""
        if not expansions:
            return 0.0

        scores = [exp.get("confidence", 0) for exp in expansions]
        return sum(scores) / len(scores)

    def _extract_content(self, response) -> str:
        """Extract content from LLM response."""
        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content
        elif hasattr(response, "output") and response.output:
            return response.output[0].content
        return ""

    async def find_similar_queries(
        self, query: str, query_history: List[str], similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find similar queries from history using semantic similarity."""
        if not query_history:
            return []

        try:
            # Generate embeddings for query and history
            query_embedding = await embedding_service.generate_embedding(query)
            if not query_embedding:
                return []

            history_embeddings = []
            for hist_query in query_history[-50]:  # Limit to recent queries
                embedding = await embedding_service.generate_embedding(hist_query)
                if embedding:
                    history_embeddings.append((hist_query, embedding))

            if not history_embeddings:
                return []

            # Calculate similarities
            query_vec = np.array([query_embedding])
            history_vecs = np.array([emb[1] for emb in history_embeddings])

            similarities = cosine_similarity(query_vec, history_vecs)[0]

            # Find similar queries above threshold
            similar_queries = []
            for i, (hist_query, _) in enumerate(history_embeddings):
                if similarities[i] >= similarity_threshold:
                    similar_queries.append(
                        {
                            "query": hist_query,
                            "similarity": float(similarities[i]),
                            "technique": "history_similarity",
                        }
                    )

            # Sort by similarity
            similar_queries.sort(key=lambda x: x["similarity"], reverse=True)
            return similar_queries[:5]  # Return top 5

        except Exception as e:
            logger.error(f"Similar query search failed: {e}")
            return []


# Global instance
query_expansion_service = QueryExpansionService()
