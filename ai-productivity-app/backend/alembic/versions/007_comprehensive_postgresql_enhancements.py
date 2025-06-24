"""Comprehensive PostgreSQL enhancements - vector storage, JSONB optimization, search

Revision ID: 007_comprehensive_postgresql_enhancements
Revises: 006_enhanced_model_configuration
Create Date: 2024-06-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = '007_comprehensive_postgresql_enhancements'
down_revision = '006_enhanced_model_configuration'
branch_labels = None
depends_on = None


def upgrade():
    """Apply comprehensive PostgreSQL enhancements"""
    
    # Get database engine to check if we're using PostgreSQL
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    if is_postgresql:
        # Enable PostgreSQL extensions
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")
        op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        
        # Try to enable pgvector (may not be available in all environments)
        try:
            op.execute("CREATE EXTENSION IF NOT EXISTS vector")
            pgvector_available = True
        except Exception:
            pgvector_available = False
            print("Warning: pgvector extension not available, skipping vector enhancements")
        
        # Create custom functions
        op.execute("""
            CREATE OR REPLACE FUNCTION normalize_code_text(text) 
            RETURNS text AS $$
            BEGIN
                -- Remove common code symbols and normalize for search
                RETURN regexp_replace(
                    regexp_replace($1, '[(){}\[\]<>;,.]', ' ', 'g'),
                    '\s+', ' ', 'g'
                );
            END;
            $$ LANGUAGE plpgsql IMMUTABLE
        """)
        
        # Create enum types
        op.execute("CREATE TYPE IF NOT EXISTS chat_role_enum AS ENUM ('user', 'assistant', 'system')")
        
        # ===== CODE DOCUMENTS ENHANCEMENTS =====
        
        # Convert JSON to JSONB
        op.execute("ALTER TABLE code_documents ALTER COLUMN symbols TYPE JSONB USING symbols::jsonb")
        op.execute("ALTER TABLE code_documents ALTER COLUMN imports TYPE JSONB USING imports::jsonb")
        op.execute("ALTER TABLE code_documents ALTER COLUMN ast_metadata TYPE JSONB USING ast_metadata::jsonb")
        
        # Add search vector column
        op.add_column('code_documents', sa.Column('search_vector', postgresql.TSVECTOR(), comment='Full-text search vector for code content'))
        
        # Create indexes for code_documents
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_project_lang 
            ON code_documents (project_id, language)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_hash 
            ON code_documents USING hash (content_hash)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_symbols_gin 
            ON code_documents USING gin (symbols)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_imports_gin 
            ON code_documents USING gin (imports)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_ast_gin 
            ON code_documents USING gin (ast_metadata)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_search_gin 
            ON code_documents USING gin (search_vector)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_path_trgm 
            ON code_documents USING gin (file_path gin_trgm_ops)
        """)
        
        # Add check constraints for code_documents
        try:
            op.execute("ALTER TABLE code_documents ADD CONSTRAINT positive_file_size CHECK (file_size >= 0)")
            op.execute("ALTER TABLE code_documents ADD CONSTRAINT symbols_is_array CHECK (jsonb_typeof(symbols) = 'array')")
            op.execute("ALTER TABLE code_documents ADD CONSTRAINT imports_is_array CHECK (jsonb_typeof(imports) = 'array')")
            op.execute("ALTER TABLE code_documents ADD CONSTRAINT ast_metadata_is_object CHECK (jsonb_typeof(ast_metadata) = 'object')")
        except Exception:
            pass  # Constraints may already exist or data may not conform
        
        # ===== CODE EMBEDDINGS ENHANCEMENTS =====
        
        # Convert JSON to JSONB  
        op.execute("ALTER TABLE code_embeddings ALTER COLUMN tags TYPE JSONB USING tags::jsonb")
        op.execute("ALTER TABLE code_embeddings ALTER COLUMN dependencies TYPE JSONB USING dependencies::jsonb")
        
        # Add pgvector column if available
        if pgvector_available:
            op.add_column('code_embeddings', sa.Column('embedding_vector', postgresql.Vector(1536), comment='Native PostgreSQL vector'))
            
            # Migrate existing embeddings to vector format
            op.execute("""
                UPDATE code_embeddings 
                SET embedding_vector = CAST(embedding::text AS vector(1536))
                WHERE embedding IS NOT NULL AND jsonb_array_length(embedding) = 1536
            """)
            
            # Create vector indexes
            op.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_embeddings_vector_cosine 
                ON code_embeddings USING ivfflat (embedding_vector vector_cosine_ops) 
                WITH (lists = 100)
            """)
            
            op.execute("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_embeddings_vector_l2 
                ON code_embeddings USING ivfflat (embedding_vector vector_l2_ops) 
                WITH (lists = 100)
            """)
        
        # Create other indexes for code_embeddings
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_embeddings_document 
            ON code_embeddings (document_id)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_embeddings_symbol 
            ON code_embeddings (symbol_name, symbol_type)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_embeddings_tags_gin 
            ON code_embeddings USING gin (tags)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_embeddings_deps_gin 
            ON code_embeddings USING gin (dependencies)
        """)
        
        # Add check constraints for code_embeddings
        try:
            op.execute("ALTER TABLE code_embeddings ADD CONSTRAINT positive_embedding_dim CHECK (embedding_dim > 0)")
            op.execute("ALTER TABLE code_embeddings ADD CONSTRAINT valid_line_range CHECK (start_line <= end_line)")
            op.execute("ALTER TABLE code_embeddings ADD CONSTRAINT tags_is_array CHECK (jsonb_typeof(tags) = 'array')")
            op.execute("ALTER TABLE code_embeddings ADD CONSTRAINT dependencies_is_object CHECK (jsonb_typeof(dependencies) = 'object')")
        except Exception:
            pass
        
        # ===== CHAT SESSIONS ENHANCEMENTS =====
        
        # Add search vector column
        op.add_column('chat_sessions', sa.Column('search_vector', postgresql.TSVECTOR(), comment='Full-text search vector for session title and summary'))
        
        # Create indexes for chat_sessions
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_sessions_title_search 
            ON chat_sessions USING gin (title gin_trgm_ops)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_sessions_active_updated 
            ON chat_sessions (is_active, updated_at) 
            WHERE is_active = true
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_sessions_summary_search 
            ON chat_sessions USING gin (summary gin_trgm_ops)
        """)
        
        # Add check constraints for chat_sessions
        try:
            op.execute("ALTER TABLE chat_sessions ADD CONSTRAINT title_length_valid CHECK (char_length(title) <= 200)")
        except Exception:
            pass
        
        # ===== CHAT MESSAGES ENHANCEMENTS =====
        
        # Add search vector column
        op.add_column('chat_messages', sa.Column('content_search', postgresql.TSVECTOR(), comment='Full-text search vector for message content'))
        
        # Create indexes for chat_messages
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_session_role_created 
            ON chat_messages (session_id, role, created_at)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_content_search 
            ON chat_messages USING gin (content gin_trgm_ops)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_code_snippets_gin 
            ON chat_messages USING gin (code_snippets)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_referenced_files_gin 
            ON chat_messages USING gin (referenced_files)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_referenced_chunks_gin 
            ON chat_messages USING gin (referenced_chunks)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_applied_commands_gin 
            ON chat_messages USING gin (applied_commands)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_active 
            ON chat_messages (session_id, created_at, role) 
            WHERE is_deleted = false
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_edited 
            ON chat_messages (session_id, edited_at) 
            WHERE is_edited = true
        """)
        
        # Add check constraints for chat_messages
        try:
            op.execute("ALTER TABLE chat_messages ADD CONSTRAINT valid_role CHECK (role IN ('user', 'assistant', 'system'))")
            op.execute("ALTER TABLE chat_messages ADD CONSTRAINT content_not_empty CHECK (char_length(content) > 0)")
            op.execute("ALTER TABLE chat_messages ADD CONSTRAINT code_snippets_is_array CHECK (jsonb_typeof(code_snippets) = 'array')")
            op.execute("ALTER TABLE chat_messages ADD CONSTRAINT referenced_files_is_array CHECK (jsonb_typeof(referenced_files) = 'array')")
            op.execute("ALTER TABLE chat_messages ADD CONSTRAINT referenced_chunks_is_array CHECK (jsonb_typeof(referenced_chunks) = 'array')")
            op.execute("ALTER TABLE chat_messages ADD CONSTRAINT applied_commands_is_object CHECK (jsonb_typeof(applied_commands) = 'object')")
        except Exception:
            pass
        
        # ===== MODEL CONFIGURATIONS - RENAME METADATA COLUMN =====
        
        # Rename metadata column to model_metadata to avoid SQLAlchemy conflicts
        try:
            op.execute("ALTER TABLE model_configurations RENAME COLUMN metadata TO model_metadata")
        except Exception:
            pass  # Column may not exist or already renamed
        
        # ===== USERS ENHANCEMENTS =====
        
        # Add new columns
        op.add_column('users', sa.Column('preferences', postgresql.JSONB(), nullable=False, server_default='{}', comment='User preferences and settings'))
        op.add_column('users', sa.Column('user_metadata', postgresql.JSONB(), nullable=False, server_default='{}', comment='Additional user metadata and profile information'))
        op.add_column('users', sa.Column('search_vector', postgresql.TSVECTOR(), comment='Full-text search vector for username and email'))
        
        # Create indexes for users
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username_trgm 
            ON users USING gin (username gin_trgm_ops)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_trgm 
            ON users USING gin (email gin_trgm_ops)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_search_gin 
            ON users USING gin (search_vector)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_preferences_gin 
            ON users USING gin (preferences)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active_login 
            ON users (is_active, last_login) 
            WHERE is_active = true
        """)
        
        # Add check constraints for users
        try:
            op.execute("ALTER TABLE users ADD CONSTRAINT username_min_length CHECK (char_length(username) >= 1)")
            op.execute("ALTER TABLE users ADD CONSTRAINT username_max_length CHECK (char_length(username) <= 50)")
            op.execute("ALTER TABLE users ADD CONSTRAINT username_format CHECK (username ~ '^[a-zA-Z0-9_-]+$')")
            op.execute("ALTER TABLE users ADD CONSTRAINT email_format CHECK (email ~ '^[^@]+@[^@]+\\.[^@]+$')")
            op.execute("ALTER TABLE users ADD CONSTRAINT email_max_length CHECK (char_length(email) <= 100)")
            op.execute("ALTER TABLE users ADD CONSTRAINT preferences_is_object CHECK (jsonb_typeof(preferences) = 'object')")
            op.execute("ALTER TABLE users ADD CONSTRAINT user_metadata_is_object CHECK (jsonb_typeof(user_metadata) = 'object')")
        except Exception:
            pass
        
        # ===== SESSIONS ENHANCEMENTS =====
        
        # Add new column
        op.add_column('sessions', sa.Column('session_metadata', postgresql.JSONB(), nullable=False, server_default='{}', comment='Session metadata (IP address, user agent, etc.)'))
        
        # Create indexes for sessions
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_created 
            ON sessions (user_id, created_at)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active 
            ON sessions (user_id, created_at) 
            WHERE revoked_at IS NULL
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_metadata_gin 
            ON sessions USING gin (session_metadata)
        """)
        
        # Add check constraints for sessions
        try:
            op.execute("ALTER TABLE sessions ADD CONSTRAINT jti_length_valid CHECK (char_length(jti) = 64)")
            op.execute("ALTER TABLE sessions ADD CONSTRAINT created_at_not_null CHECK (created_at IS NOT NULL)")
            op.execute("ALTER TABLE sessions ADD CONSTRAINT session_metadata_is_object CHECK (jsonb_typeof(session_metadata) = 'object')")
        except Exception:
            pass
        
        # ===== SEARCH VECTOR TRIGGERS =====
        
        # Create trigger functions for automatic search vector updates
        op.execute("""
            CREATE OR REPLACE FUNCTION update_search_vectors()
            RETURNS TRIGGER AS $$
            BEGIN
                CASE TG_TABLE_NAME
                    WHEN 'users' THEN
                        NEW.search_vector := to_tsvector('simple', NEW.username || ' ' || NEW.email);
                    WHEN 'chat_sessions' THEN
                        NEW.search_vector := to_tsvector('ai_english', 
                            COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.summary, ''));
                    WHEN 'chat_messages' THEN
                        NEW.content_search := to_tsvector('ai_english', NEW.content);
                    WHEN 'code_documents' THEN
                        NEW.search_vector := to_tsvector('ai_english', 
                            normalize_code_text(NEW.file_path || ' ' || COALESCE(NEW.symbols::text, '')));
                END CASE;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        
        # Create triggers
        op.execute("""
            CREATE TRIGGER users_search_update
                BEFORE INSERT OR UPDATE ON users
                FOR EACH ROW EXECUTE FUNCTION update_search_vectors()
        """)
        
        op.execute("""
            CREATE TRIGGER chat_sessions_search_update
                BEFORE INSERT OR UPDATE ON chat_sessions
                FOR EACH ROW EXECUTE FUNCTION update_search_vectors()
        """)
        
        op.execute("""
            CREATE TRIGGER chat_messages_search_update
                BEFORE INSERT OR UPDATE ON chat_messages
                FOR EACH ROW EXECUTE FUNCTION update_search_vectors()
        """)
        
        op.execute("""
            CREATE TRIGGER code_documents_search_update
                BEFORE INSERT OR UPDATE ON code_documents
                FOR EACH ROW EXECUTE FUNCTION update_search_vectors()
        """)
        
        # ===== MATERIALIZED VIEWS FOR ANALYTICS =====
        
        op.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS project_analytics AS
            SELECT 
                p.id,
                p.title,
                p.status,
                COUNT(DISTINCT cs.id) as chat_sessions_count,
                COUNT(DISTINCT cm.id) as chat_messages_count,
                COUNT(DISTINCT cd.id) as code_documents_count,
                COUNT(DISTINCT te.id) as timeline_events_count,
                MAX(cs.updated_at) as last_chat_activity,
                MAX(te.created_at) as last_timeline_activity,
                AVG(CASE WHEN cm.role = 'assistant' THEN char_length(cm.content) END) as avg_response_length
            FROM projects p
            LEFT JOIN chat_sessions cs ON p.id = cs.project_id
            LEFT JOIN chat_messages cm ON cs.id = cm.session_id AND cm.is_deleted = false
            LEFT JOIN code_documents cd ON p.id = cd.project_id
            LEFT JOIN timeline_events te ON p.id = te.project_id
            GROUP BY p.id, p.title, p.status
        """)
        
        # Create unique index on materialized view
        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_project_analytics_id ON project_analytics (id)")
        
        print("PostgreSQL enhancements applied successfully!")
        
    else:
        print("Skipping PostgreSQL-specific enhancements (not using PostgreSQL)")


def downgrade():
    """Remove comprehensive PostgreSQL enhancements"""
    
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    if is_postgresql:
        # Drop materialized view
        op.execute("DROP MATERIALIZED VIEW IF EXISTS project_analytics")
        
        # Drop triggers
        op.execute("DROP TRIGGER IF EXISTS users_search_update ON users")
        op.execute("DROP TRIGGER IF EXISTS chat_sessions_search_update ON chat_sessions")
        op.execute("DROP TRIGGER IF EXISTS chat_messages_search_update ON chat_messages")
        op.execute("DROP TRIGGER IF EXISTS code_documents_search_update ON code_documents")
        
        # Drop trigger function
        op.execute("DROP FUNCTION IF EXISTS update_search_vectors()")
        op.execute("DROP FUNCTION IF EXISTS normalize_code_text(text)")
        
        # Drop enum types
        op.execute("DROP TYPE IF EXISTS chat_role_enum")
        
        # Revert model_configurations metadata column rename
        try:
            op.execute("ALTER TABLE model_configurations RENAME COLUMN model_metadata TO metadata")
        except Exception:
            pass
        
        # Remove added columns
        op.drop_column('sessions', 'session_metadata')
        op.drop_column('users', 'search_vector')
        op.drop_column('users', 'user_metadata')
        op.drop_column('users', 'preferences')
        op.drop_column('chat_messages', 'content_search')
        op.drop_column('chat_sessions', 'search_vector')
        op.drop_column('code_documents', 'search_vector')
        
        # Try to remove pgvector column if it exists
        try:
            op.drop_column('code_embeddings', 'embedding_vector')
        except Exception:
            pass
        
        # Drop all indexes created (they will be dropped automatically with column drops)
        indexes_to_drop = [
            'idx_code_documents_project_lang', 'idx_code_documents_hash',
            'idx_code_documents_symbols_gin', 'idx_code_documents_imports_gin',
            'idx_code_documents_ast_gin', 'idx_code_documents_search_gin',
            'idx_code_documents_path_trgm', 'idx_code_embeddings_vector_cosine',
            'idx_code_embeddings_vector_l2', 'idx_code_embeddings_document',
            'idx_code_embeddings_symbol', 'idx_code_embeddings_tags_gin',
            'idx_code_embeddings_deps_gin', 'idx_chat_sessions_title_search',
            'idx_chat_sessions_active_updated', 'idx_chat_sessions_summary_search',
            'idx_chat_messages_session_role_created', 'idx_chat_messages_content_search',
            'idx_chat_messages_code_snippets_gin', 'idx_chat_messages_referenced_files_gin',
            'idx_chat_messages_referenced_chunks_gin', 'idx_chat_messages_applied_commands_gin',
            'idx_chat_messages_active', 'idx_chat_messages_edited',
            'idx_users_username_trgm', 'idx_users_email_trgm',
            'idx_users_search_gin', 'idx_users_preferences_gin',
            'idx_users_active_login', 'idx_sessions_user_created',
            'idx_sessions_active', 'idx_sessions_metadata_gin'
        ]
        
        for index_name in indexes_to_drop:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}")
        
        # Drop check constraints
        constraints_to_drop = [
            ('code_documents', ['positive_file_size', 'symbols_is_array', 'imports_is_array', 'ast_metadata_is_object']),
            ('code_embeddings', ['positive_embedding_dim', 'valid_line_range', 'tags_is_array', 'dependencies_is_object']),
            ('chat_sessions', ['title_length_valid']),
            ('chat_messages', ['valid_role', 'content_not_empty', 'code_snippets_is_array', 'referenced_files_is_array', 'referenced_chunks_is_array', 'applied_commands_is_object']),
            ('users', ['username_min_length', 'username_max_length', 'username_format', 'email_format', 'email_max_length', 'preferences_is_object', 'user_metadata_is_object']),
            ('sessions', ['jti_length_valid', 'created_at_not_null', 'session_metadata_is_object'])
        ]
        
        for table_name, constraints in constraints_to_drop:
            for constraint in constraints:
                try:
                    op.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint}")
                except Exception:
                    pass
        
        # Revert JSONB back to JSON
        tables_to_revert = [
            ('code_documents', ['symbols', 'imports', 'ast_metadata']),
            ('code_embeddings', ['tags', 'dependencies'])
        ]
        
        for table_name, columns in tables_to_revert:
            for column in columns:
                try:
                    op.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column} TYPE JSON USING {column}::json")
                except Exception:
                    pass