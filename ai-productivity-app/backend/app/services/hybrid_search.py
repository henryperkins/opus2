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
from app.services.git_history_searcher import GitHistorySearcher
from app.services.static_analysis_searcher import StaticAnalysisSearcher
from app.services.summarization_service import SummarizationService
from app.embeddings.generator import EmbeddingGenerator
from app.utils.token_counter import count_tokens

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
        self.summarization_service = SummarizationService()

        # Default search weights
        self.default_weights = {"semantic": 0.5, "keyword": 0.3, "structural": 0.2}
        
        # Query type specific weights
        self.query_type_weights = {
            "error_debug": {"semantic": 0.3, "keyword": 0.6, "structural": 0.1},
            "api_usage": {"semantic": 0.6, "keyword": 0.2, "structural": 0.2}, 
            "implementation": {"semantic": 0.7, "keyword": 0.2, "structural": 0.1},
            "conceptual": {"semantic": 0.8, "keyword": 0.1, "structural": 0.1},
            "specific_code": {"semantic": 0.2, "keyword": 0.3, "structural": 0.5},
            "performance": {"semantic": 0.4, "keyword": 0.4, "structural": 0.2},
            "testing": {"semantic": 0.4, "keyword": 0.5, "structural": 0.1}
        }

    async def search(
        self,
        query: str,
        project_ids: List[int],
        filters: Optional[Dict] = None,
        limit: int = 20,
        search_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Execute hybrid search across all modalities."""
        # ------------------------------------------------------------------
        # `filters` can either be a plain ``dict`` **or** a Pydantic model
        # (``SearchFilters``) depending on where `HybridSearch.search` is being
        # called from.  Down-stream services (keyword/structural search, vector
        # filtering, …) expect *mapping* semantics and use ``filters.get``.
        # To be defensive we therefore convert the object to a plain dict
        # early on so that the remainder of the code never needs to care about
        # the concrete type.
        # ------------------------------------------------------------------

        if filters is not None and not isinstance(filters, dict):
            # Pydantic v2 → ``model_dump``
            if hasattr(filters, "model_dump"):
                filters = filters.model_dump(exclude_none=True)  # type: ignore[attr-defined]
            # Pydantic v1 → ``dict``
            elif hasattr(filters, "dict"):
                filters = filters.dict(exclude_none=True)  # type: ignore[attr-defined]
            else:  # Fallback – should not normally happen
                filters = {
                    k: v
                    for k, v in getattr(filters, "__dict__", {}).items()
                    if (not k.startswith("_")) and k not in {"model_config", "model_fields"}
                }

        if not search_types:
            search_types = ["semantic", "keyword", "structural"]
            
        # Detect query type and adjust weights
        query_type = self._detect_query_type(query)
        weights = self.query_type_weights.get(query_type, self.default_weights)
        
        logger.info(f"Query type detected: {query_type}, using weights: {weights}")

        # Check if structural search applies
        structural_parsed = self.structural_search._parse_query(query)
        if structural_parsed:
            search_type = structural_parsed.get("type")
            
            # Handle Git History searches
            if search_type in ["commit", "blame"]:
                # For Git searches, we need to determine the repository path
                # Using the first project_id as the primary project
                if project_ids:
                    # Simple path construction - in production, you'd query the database
                    # to get the actual repository path
                    project_repo_path = f"repos/project_{project_ids[0]}"
                    git_searcher = GitHistorySearcher(project_repo_path)
                    
                    if search_type == "commit":
                        return git_searcher.search_commits(structural_parsed["term"], limit)
                    elif search_type == "blame":
                        return git_searcher.get_blame(structural_parsed["file"], structural_parsed["line"])
            
            # Handle documentation searches
            elif search_type == "doc":
                # If it's a doc search, modify the query and add a filter
                query = structural_parsed["term"]
                if filters is None:
                    filters = {}
                # Add a filter to only search in documentation files
                filters["file_path_pattern"] = "**/*.md"
                # Force only semantic and keyword search for docs
                search_types = ["semantic", "keyword"]
            
            # Handle static analysis/linting
            elif search_type == "lint":
                if project_ids:
                    project_repo_path = f"repos/project_{project_ids[0]}"
                    analysis_searcher = StaticAnalysisSearcher(project_repo_path)
                    return analysis_searcher.run_pylint(structural_parsed["term"])
            
            else:
                # Prioritize structural search for other specific queries
                search_types = ["structural"]

        # Execute searches in parallel
        tasks = []
        if "semantic" in search_types and self.embedding_generator:
            tasks.append(self._semantic_search(query, project_ids, filters, limit, weights["semantic"]))
        if "keyword" in search_types:
            tasks.append(self._keyword_search_with_weight(query, project_ids, filters, limit, weights["keyword"]))
        if "structural" in search_types:
            tasks.append(self._structural_search_with_weight(query, project_ids, filters, limit, weights["structural"]))

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
        self, query: str, project_ids: List[int], filters: Optional[Dict], limit: int, weight: float
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
                        "score": result["score"] * weight,
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
    
    async def _keyword_search_with_weight(
        self, query: str, project_ids: List[int], filters: Optional[Dict], limit: int, weight: float
    ) -> List[Dict]:
        """Execute keyword search with weight applied."""
        results = await self.keyword_search.search(query, project_ids, filters, limit)
        
        # Apply weight to scores
        for result in results:
            if "score" in result:
                result["score"] *= weight
                
        return results
    
    async def _structural_search_with_weight(
        self, query: str, project_ids: List[int], filters: Optional[Dict], limit: int, weight: float
    ) -> List[Dict]:
        """Execute structural search with weight applied."""
        results = await self.structural_search.search(query, project_ids, filters, limit)
        
        # Apply weight to scores  
        for result in results:
            if "score" in result:
                result["score"] *= weight
                
        return results
    
    def _detect_query_type(self, query: str) -> str:
        """Detect the type of query to apply appropriate weights."""
        query_lower = query.lower()
        
        # Error/debugging patterns
        error_patterns = [
            "error", "exception", "traceback", "bug", "issue", "problem", 
            "failed", "broken", "crash", "debug", "stacktrace", "TypeError",
            "ValueError", "AttributeError", "fix", "wrong", "not working"
        ]
        
        # API usage patterns
        api_patterns = [
            "api", "endpoint", "request", "response", "http", "rest", 
            "get", "post", "put", "delete", "route", "handler"
        ]
        
        # Implementation patterns
        impl_patterns = [
            "implement", "create", "build", "make", "add", "develop",
            "design", "architecture", "pattern", "approach", "solution"
        ]
        
        # Conceptual patterns
        conceptual_patterns = [
            "how", "what", "why", "when", "explain", "understand", 
            "concept", "principle", "theory", "overview", "summary"
        ]
        
        # Specific code patterns
        specific_patterns = [
            "function", "class", "method", "variable", "constant",
            "import", "module", "package", "file:", "line", "@"
        ]
        
        # Performance patterns
        performance_patterns = [
            "performance", "optimize", "speed", "fast", "slow", "efficient",
            "memory", "cpu", "benchmark", "profil", "cache", "scale"
        ]
        
        # Testing patterns
        testing_patterns = [
            "test", "testing", "unit test", "integration", "mock", "assert",
            "coverage", "pytest", "unittest", "spec", "tdd"
        ]
        
        # Count matches for each pattern type
        pattern_counts = {
            "error_debug": sum(1 for p in error_patterns if p in query_lower),
            "api_usage": sum(1 for p in api_patterns if p in query_lower),
            "implementation": sum(1 for p in impl_patterns if p in query_lower),
            "conceptual": sum(1 for p in conceptual_patterns if p in query_lower),
            "specific_code": sum(1 for p in specific_patterns if p in query_lower),
            "performance": sum(1 for p in performance_patterns if p in query_lower),
            "testing": sum(1 for p in testing_patterns if p in query_lower)
        }
        
        # Additional heuristics
        # Queries with specific symbols or file references are likely specific_code
        if any(char in query for char in ["(", ")", ".", "::"]) or "def " in query_lower:
            pattern_counts["specific_code"] += 2
            
        # Questions starting with "how" are often conceptual unless they contain implementation words
        if query_lower.startswith("how"):
            if any(p in query_lower for p in impl_patterns):
                pattern_counts["implementation"] += 1
            else:
                pattern_counts["conceptual"] += 1
                
        # Queries with stack traces or error messages
        if any(term in query_lower for term in ["traceback", "at line", "line ", "error:"]):
            pattern_counts["error_debug"] += 2
        
        # Return the type with highest count, default to conceptual
        if not any(pattern_counts.values()):
            return "conceptual"
            
        return max(pattern_counts.keys(), key=lambda k: pattern_counts[k])

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
        """Get relevant context for LLM prompts with intelligent summarization."""
        results = await self.search(query, project_ids, limit=15)  # Get more candidates
        
        if not results:
            return ""

        # Reserve tokens for summary if needed
        main_context_tokens = int(max_tokens * 0.7)  # 70% for main content
        summary_tokens = max_tokens - main_context_tokens  # 30% for summary
        
        # Determine which chunks to keep vs summarize
        kept_chunks, overflow_chunks = self.summarization_service.should_summarize_chunks(
            results, main_context_tokens, keep_top_n=6
        )
        
        # Format main context
        context_parts = []
        for result in kept_chunks:
            metadata = result.get("metadata", {})

            # Format context
            context = f"\n# File: {metadata.get('file_path', 'Unknown')}"
            if metadata.get("symbol_name"):
                context += f"\n# {metadata['symbol_type']}: {metadata['symbol_name']}"
            if metadata.get("start_line"):
                context += f" (lines {metadata['start_line']}-{metadata['end_line']})"
            context += f"\n\n{result['content']}\n"
            context_parts.append(context)

        main_context = "\n---\n".join(context_parts)
        
        # Add summary if there are overflow chunks
        if overflow_chunks:
            try:
                # Extract focus areas from query for better summarization
                focus_areas = self._extract_focus_areas(query)
                
                summary = await self.summarization_service.summarize_overflow_chunks(
                    overflow_chunks, 
                    query_context=query,
                    focus_areas=focus_areas
                )
                
                if summary:
                    return f"{main_context}\n\n---\n\n{summary}"
            except Exception as e:
                logger.warning(f"Failed to summarize overflow chunks: {e}")
        
        return main_context
    
    def _extract_focus_areas(self, query: str) -> List[str]:
        """Extract potential focus areas from the user query."""
        focus_keywords = {
            "error": ["error handling", "exceptions", "debugging"],
            "test": ["testing", "unit tests", "test cases"],
            "performance": ["optimization", "speed", "efficiency"],
            "security": ["authentication", "authorization", "validation"],
            "api": ["endpoints", "routes", "requests"],
            "database": ["models", "queries", "migrations"],
            "config": ["configuration", "settings", "environment"],
            "deploy": ["deployment", "production", "scaling"]
        }
        
        query_lower = query.lower()
        focus_areas = []
        
        for keyword, areas in focus_keywords.items():
            if keyword in query_lower:
                focus_areas.extend(areas)
        
        return focus_areas[:3]  # Limit to top 3 focus areas
