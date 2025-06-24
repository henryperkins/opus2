"""PostgreSQL optimizations - indexes and JSONB

Revision ID: 005_postgresql_optimizations
Revises: 004_add_import_jobs
Create Date: 2024-06-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = '005_postgresql_optimizations'
down_revision = '004_add_import_jobs'
branch_labels = None
depends_on = None


def upgrade():
    """Add PostgreSQL-specific optimizations"""
    
    # Get database engine to check if we're using PostgreSQL
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    if is_postgresql:
        # Create indexes for full-text search
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_fts 
            ON projects USING gin(to_tsvector('ai_english', title || ' ' || COALESCE(description, '')))
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_fts 
            ON chat_messages USING gin(to_tsvector('ai_english', content))
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_fts 
            ON code_documents USING gin(to_tsvector('ai_english', normalize_code_text(file_path)))
        """)
        
        # Create GIN indexes for JSON/JSONB columns
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_tags_gin 
            ON projects USING gin(tags)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_metadata_gin 
            ON chat_messages USING gin(code_snippets, referenced_files, referenced_chunks, applied_commands)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_symbols_gin 
            ON code_documents USING gin(symbols)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_embeddings_tags_gin 
            ON code_embeddings USING gin(tags)
        """)
        
        # Create composite indexes for common query patterns
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_session_active 
            ON chat_messages (session_id, is_deleted) 
            WHERE is_deleted = false
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_project_lang 
            ON code_documents (project_id, language) 
            WHERE language IS NOT NULL
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_timeline_events_project_type 
            ON timeline_events (project_id, event_type, created_at)
        """)
        
        # Create partial indexes for active/non-deleted records
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_active 
            ON projects (owner_id, status, created_at) 
            WHERE status != 'ARCHIVED'
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_sessions_active 
            ON chat_sessions (project_id, is_active, updated_at) 
            WHERE is_active = true
        """)
        
        # Create trigram indexes for fuzzy search
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_title_trgm 
            ON projects USING gin(title gin_trgm_ops)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_documents_path_trgm 
            ON code_documents USING gin(file_path gin_trgm_ops)
        """)
        
        # Placeholder for vector indexes (when pgvector is available)
        # op.execute("""
        #     CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_code_embeddings_vector_cosine 
        #     ON code_embeddings USING ivfflat (embedding vector_cosine_ops) 
        #     WITH (lists = 100)
        # """)


def downgrade():
    """Remove PostgreSQL-specific optimizations"""
    
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    if is_postgresql:
        # Drop all the indexes we created
        indexes_to_drop = [
            'idx_projects_fts',
            'idx_chat_messages_fts', 
            'idx_code_documents_fts',
            'idx_projects_tags_gin',
            'idx_chat_messages_metadata_gin',
            'idx_code_documents_symbols_gin',
            'idx_code_embeddings_tags_gin',
            'idx_chat_messages_session_active',
            'idx_code_documents_project_lang',
            'idx_timeline_events_project_type',
            'idx_projects_active',
            'idx_chat_sessions_active',
            'idx_projects_title_trgm',
            'idx_code_documents_path_trgm',
            # 'idx_code_embeddings_vector_cosine'
        ]
        
        for index_name in indexes_to_drop:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}")