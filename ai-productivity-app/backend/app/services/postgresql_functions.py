"""PostgreSQL-specific functions and utilities for advanced database operations."""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class PostgreSQLFunctions:
    """PostgreSQL-specific database functions and utilities."""

    def __init__(self, db: Session):
        self.db = db
        self.is_postgresql = db.bind.dialect.name == "postgresql"

    def create_advanced_functions(self):
        """Create advanced PostgreSQL functions for enhanced search and analytics."""
        if not self.is_postgresql:
            logger.warning("Advanced functions require PostgreSQL")
            return

        # Function for intelligent code similarity search
        self.db.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION find_similar_code(
                query_vector vector(1536),
                project_filter int[] DEFAULT NULL,
                language_filter text DEFAULT NULL,
                similarity_threshold float DEFAULT 0.8,
                result_limit int DEFAULT 10
            )
            RETURNS TABLE(
                document_id int,
                chunk_id int,
                similarity_score float,
                content text,
                file_path text,
                symbol_name text,
                symbol_type text
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    cd.id as document_id,
                    ce.id as chunk_id,
                    1 - (ce.embedding_vector <=> query_vector) as similarity,
                    ce.chunk_content as content,
                    cd.file_path,
                    ce.symbol_name,
                    ce.symbol_type
                FROM code_embeddings ce
                JOIN code_documents cd ON ce.document_id = cd.id
                WHERE 
                    (project_filter IS NULL OR cd.project_id = ANY(project_filter))
                    AND (language_filter IS NULL OR cd.language = language_filter)
                    AND ce.embedding_vector IS NOT NULL
                    AND (1 - (ce.embedding_vector <=> query_vector)) >= similarity_threshold
                ORDER BY ce.embedding_vector <=> query_vector
                LIMIT result_limit;
            END;
            $$ LANGUAGE plpgsql;
        """
            )
        )

        # Function for hybrid search combining vector and text search
        self.db.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION hybrid_code_search(
                search_query text,
                query_vector vector(1536) DEFAULT NULL,
                project_filter int[] DEFAULT NULL,
                vector_weight float DEFAULT 0.6,
                text_weight float DEFAULT 0.4,
                result_limit int DEFAULT 20
            )
            RETURNS TABLE(
                document_id int,
                chunk_id int,
                combined_score float,
                vector_score float,
                text_score float,
                content text,
                file_path text,
                symbol_name text
            ) AS $$
            BEGIN
                RETURN QUERY
                WITH vector_results AS (
                    SELECT 
                        cd.id as doc_id,
                        ce.id as chunk_id,
                        CASE 
                            WHEN query_vector IS NOT NULL AND ce.embedding_vector IS NOT NULL 
                            THEN 1 - (ce.embedding_vector <=> query_vector)
                            ELSE 0 
                        END as v_score,
                        ce.chunk_content,
                        cd.file_path,
                        ce.symbol_name
                    FROM code_embeddings ce
                    JOIN code_documents cd ON ce.document_id = cd.id
                    WHERE project_filter IS NULL OR cd.project_id = ANY(project_filter)
                ),
                text_results AS (
                    SELECT 
                        cd.id as doc_id,
                        ce.id as chunk_id,
                        ts_rank(
                            to_tsvector('ai_english', ce.chunk_content || ' ' || COALESCE(ce.symbol_name, '')),
                            plainto_tsquery('ai_english', search_query)
                        ) as t_score,
                        ce.chunk_content,
                        cd.file_path,
                        ce.symbol_name
                    FROM code_embeddings ce
                    JOIN code_documents cd ON ce.document_id = cd.id
                    WHERE 
                        (project_filter IS NULL OR cd.project_id = ANY(project_filter))
                        AND to_tsvector('ai_english', ce.chunk_content || ' ' || COALESCE(ce.symbol_name, '')) 
                            @@ plainto_tsquery('ai_english', search_query)
                )
                SELECT 
                    COALESCE(v.doc_id, t.doc_id) as document_id,
                    COALESCE(v.chunk_id, t.chunk_id) as chunk_id,
                    (COALESCE(v.v_score, 0) * vector_weight + COALESCE(t.t_score, 0) * text_weight) as combined_score,
                    COALESCE(v.v_score, 0) as vector_score,
                    COALESCE(t.t_score, 0) as text_score,
                    COALESCE(v.chunk_content, t.chunk_content) as content,
                    COALESCE(v.file_path, t.file_path) as file_path,
                    COALESCE(v.symbol_name, t.symbol_name) as symbol_name
                FROM vector_results v
                FULL OUTER JOIN text_results t ON v.chunk_id = t.chunk_id
                WHERE (COALESCE(v.v_score, 0) * vector_weight + COALESCE(t.t_score, 0) * text_weight) > 0
                ORDER BY combined_score DESC
                LIMIT result_limit;
            END;
            $$ LANGUAGE plpgsql;
        """
            )
        )

        # Function for advanced chat search with context
        self.db.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION search_chat_with_context(
                search_query text,
                project_filter int[] DEFAULT NULL,
                session_filter int[] DEFAULT NULL,
                include_context boolean DEFAULT true,
                context_window int DEFAULT 2,
                result_limit int DEFAULT 50
            )
            RETURNS TABLE(
                message_id int,
                session_id int,
                project_id int,
                content text,
                role text,
                created_at timestamp,
                rank_score float,
                context_before text,
                context_after text
            ) AS $$
            BEGIN
                RETURN QUERY
                WITH ranked_messages AS (
                    SELECT 
                        cm.id,
                        cm.session_id,
                        cs.project_id,
                        cm.content,
                        cm.role,
                        cm.created_at,
                        ts_rank(
                            cm.content_search,
                            plainto_tsquery('ai_english', search_query)
                        ) as rank_score,
                        ROW_NUMBER() OVER (PARTITION BY cm.session_id ORDER BY cm.created_at) as msg_num
                    FROM chat_messages cm
                    JOIN chat_sessions cs ON cm.session_id = cs.id
                    WHERE 
                        cm.is_deleted = false
                        AND cm.content_search @@ plainto_tsquery('ai_english', search_query)
                        AND (project_filter IS NULL OR cs.project_id = ANY(project_filter))
                        AND (session_filter IS NULL OR cm.session_id = ANY(session_filter))
                )
                SELECT 
                    rm.id as message_id,
                    rm.session_id,
                    rm.project_id,
                    rm.content,
                    rm.role,
                    rm.created_at,
                    rm.rank_score,
                    CASE WHEN include_context THEN (
                        SELECT string_agg(prev_cm.content, ' | ' ORDER BY prev_cm.created_at)
                        FROM chat_messages prev_cm
                        WHERE prev_cm.session_id = rm.session_id 
                        AND prev_cm.created_at < rm.created_at
                        AND prev_cm.is_deleted = false
                        ORDER BY prev_cm.created_at DESC
                        LIMIT context_window
                    ) ELSE NULL END as context_before,
                    CASE WHEN include_context THEN (
                        SELECT string_agg(next_cm.content, ' | ' ORDER BY next_cm.created_at)
                        FROM chat_messages next_cm
                        WHERE next_cm.session_id = rm.session_id 
                        AND next_cm.created_at > rm.created_at
                        AND next_cm.is_deleted = false
                        ORDER BY next_cm.created_at ASC
                        LIMIT context_window
                    ) ELSE NULL END as context_after
                FROM ranked_messages rm
                ORDER BY rm.rank_score DESC, rm.created_at DESC
                LIMIT result_limit;
            END;
            $$ LANGUAGE plpgsql;
        """
            )
        )

        # Function for project analytics with time-based filtering
        self.db.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION get_project_analytics(
                project_filter int[] DEFAULT NULL,
                time_period interval DEFAULT '30 days'
            )
            RETURNS TABLE(
                project_id int,
                project_title text,
                total_chat_messages int,
                total_code_files int,
                avg_response_length float,
                activity_score float,
                last_activity timestamp,
                top_languages text[]
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    p.id as project_id,
                    p.title as project_title,
                    COUNT(DISTINCT cm.id)::int as total_chat_messages,
                    COUNT(DISTINCT cd.id)::int as total_code_files,
                    AVG(char_length(cm.content))::float as avg_response_length,
                    (COUNT(DISTINCT cm.id) * 0.6 + COUNT(DISTINCT cd.id) * 0.4)::float as activity_score,
                    MAX(GREATEST(cm.created_at, cd.created_at)) as last_activity,
                    array_agg(DISTINCT cd.language ORDER BY COUNT(*) DESC) FILTER (WHERE cd.language IS NOT NULL) as top_languages
                FROM projects p
                LEFT JOIN chat_sessions cs ON p.id = cs.project_id
                LEFT JOIN chat_messages cm ON cs.id = cm.session_id 
                    AND cm.created_at > CURRENT_TIMESTAMP - time_period
                    AND cm.is_deleted = false
                LEFT JOIN code_documents cd ON p.id = cd.project_id
                    AND cd.created_at > CURRENT_TIMESTAMP - time_period
                WHERE 
                    p.status != 'ARCHIVED'
                    AND (project_filter IS NULL OR p.id = ANY(project_filter))
                GROUP BY p.id, p.title
                HAVING COUNT(DISTINCT cm.id) > 0 OR COUNT(DISTINCT cd.id) > 0
                ORDER BY activity_score DESC, last_activity DESC;
            END;
            $$ LANGUAGE plpgsql;
        """
            )
        )

        # Function for intelligent model recommendations based on usage patterns
        self.db.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION recommend_models_for_task(
                task_type text DEFAULT 'chat',
                project_context jsonb DEFAULT '{}',
                performance_priority text DEFAULT 'balanced'
            )
            RETURNS TABLE(
                model_id text,
                name text,
                provider text,
                score float,
                reason text
            ) AS $$
            BEGIN
                RETURN QUERY
                WITH model_scores AS (
                    SELECT 
                        mc.model_id,
                        mc.name,
                        mc.provider::text,
                        CASE performance_priority
                            WHEN 'speed' THEN 
                                (1.0 / NULLIF(mc.avg_response_time_ms, 0)) * 0.6 +
                                (mc.throughput_tokens_per_sec / 100.0) * 0.4
                            WHEN 'cost' THEN
                                (1.0 / NULLIF(mc.cost_input_per_1k + mc.cost_output_per_1k, 0)) * 0.8 +
                                (mc.throughput_tokens_per_sec / 100.0) * 0.2
                            ELSE -- 'balanced'
                                (1.0 / NULLIF(mc.avg_response_time_ms, 0)) * 0.3 +
                                (mc.throughput_tokens_per_sec / 100.0) * 0.3 +
                                (1.0 / NULLIF(mc.cost_input_per_1k + mc.cost_output_per_1k, 0)) * 0.4
                        END as base_score,
                        CASE 
                            WHEN task_type = ANY(SELECT jsonb_array_elements_text(mc.capabilities))
                            THEN 'Perfect match for task type'
                            WHEN 'chat' = ANY(SELECT jsonb_array_elements_text(mc.capabilities))
                            THEN 'General chat capability'
                            ELSE 'Basic capability'
                        END as match_reason
                    FROM model_configurations mc
                    WHERE mc.is_available = true AND mc.is_deprecated = false
                )
                SELECT 
                    ms.model_id,
                    ms.name,
                    ms.provider,
                    ms.base_score as score,
                    ms.match_reason as reason
                FROM model_scores ms
                WHERE ms.base_score > 0
                ORDER BY ms.base_score DESC
                LIMIT 5;
            END;
            $$ LANGUAGE plpgsql;
        """
            )
        )

        self.db.commit()
        logger.info("Advanced PostgreSQL functions created successfully")

    def find_similar_code(
        self,
        query_vector: List[float],
        project_ids: Optional[List[int]] = None,
        language: Optional[str] = None,
        threshold: float = 0.8,
        limit: int = 10,
    ) -> List[Dict]:
        """Find similar code using vector similarity."""
        if not self.is_postgresql:
            return []

        result = self.db.execute(
            text(
                """
            SELECT * FROM find_similar_code(
                :query_vector::vector(1536),
                :project_filter,
                :language_filter,
                :similarity_threshold,
                :result_limit
            )
        """
            ),
            {
                "query_vector": str(query_vector),
                "project_filter": project_ids,
                "language_filter": language,
                "similarity_threshold": threshold,
                "result_limit": limit,
            },
        )

        return [dict(row) for row in result]

    def hybrid_search(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        project_ids: Optional[List[int]] = None,
        vector_weight: float = 0.6,
        text_weight: float = 0.4,
        limit: int = 20,
    ) -> List[Dict]:
        """Perform hybrid search combining vector and text search."""
        if not self.is_postgresql:
            return []

        result = self.db.execute(
            text(
                """
            SELECT * FROM hybrid_code_search(
                :search_query,
                :query_vector::vector(1536),
                :project_filter,
                :vector_weight,
                :text_weight,
                :result_limit
            )
        """
            ),
            {
                "search_query": query,
                "query_vector": str(query_vector) if query_vector else None,
                "project_filter": project_ids,
                "vector_weight": vector_weight,
                "text_weight": text_weight,
                "result_limit": limit,
            },
        )

        return [dict(row) for row in result]

    def search_chat_with_context(
        self,
        query: str,
        project_ids: Optional[List[int]] = None,
        session_ids: Optional[List[int]] = None,
        include_context: bool = True,
        context_window: int = 2,
        limit: int = 50,
    ) -> List[Dict]:
        """Search chat messages with surrounding context."""
        if not self.is_postgresql:
            return []

        result = self.db.execute(
            text(
                """
            SELECT * FROM search_chat_with_context(
                :search_query,
                :project_filter,
                :session_filter,
                :include_context,
                :context_window,
                :result_limit
            )
        """
            ),
            {
                "search_query": query,
                "project_filter": project_ids,
                "session_filter": session_ids,
                "include_context": include_context,
                "context_window": context_window,
                "result_limit": limit,
            },
        )

        return [dict(row) for row in result]

    def get_project_analytics(
        self, project_ids: Optional[List[int]] = None, time_period: str = "30 days"
    ) -> List[Dict]:
        """Get comprehensive project analytics."""
        if not self.is_postgresql:
            return []

        result = self.db.execute(
            text(
                """
            SELECT * FROM get_project_analytics(
                :project_filter,
                :time_period::interval
            )
        """
            ),
            {"project_filter": project_ids, "time_period": time_period},
        )

        return [dict(row) for row in result]

    def recommend_models(
        self,
        task_type: str = "chat",
        project_context: Dict[str, Any] = None,
        performance_priority: str = "balanced",
    ) -> List[Dict]:
        """Get model recommendations based on task and context."""
        if not self.is_postgresql:
            return []

        result = self.db.execute(
            text(
                """
            SELECT * FROM recommend_models_for_task(
                :task_type,
                :project_context::jsonb,
                :performance_priority
            )
        """
            ),
            {
                "task_type": task_type,
                "project_context": str(project_context or {}),
                "performance_priority": performance_priority,
            },
        )

        return [dict(row) for row in result]

    def refresh_materialized_views(self):
        """Refresh all materialized views for updated analytics."""
        if not self.is_postgresql:
            return

        self.db.execute(text("REFRESH MATERIALIZED VIEW project_analytics"))
        self.db.commit()
        logger.info("Materialized views refreshed")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        if not self.is_postgresql:
            return {}

        # Query performance statistics
        result = self.db.execute(
            text(
                """
            SELECT 
                query,
                calls,
                total_exec_time,
                mean_exec_time,
                min_exec_time,
                max_exec_time
            FROM pg_stat_statements 
            WHERE query NOT LIKE '%pg_stat_statements%'
            ORDER BY mean_exec_time DESC 
            LIMIT 10
        """
            )
        )

        slow_queries = [dict(row) for row in result]

        # Index usage statistics
        result = self.db.execute(
            text(
                """
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes 
            ORDER BY idx_scan DESC 
            LIMIT 20
        """
            )
        )

        index_stats = [dict(row) for row in result]

        # Database size information
        result = self.db.execute(
            text(
                """
            SELECT 
                pg_size_pretty(pg_database_size(current_database())) as database_size,
                count(*) as active_connections
            FROM pg_stat_activity 
            WHERE state = 'active'
        """
            )
        )

        db_info = dict(result.fetchone())

        return {
            "slow_queries": slow_queries,
            "index_usage": index_stats,
            "database_info": db_info,
        }
