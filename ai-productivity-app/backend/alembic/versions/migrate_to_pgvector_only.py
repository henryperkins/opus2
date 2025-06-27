"""Migrate to pgvector-only backend

This migration:
1. Enables the pgvector extension
2. Creates the embeddings table for code embeddings
3. Adds necessary indexes for vector similarity search

Revision ID: migrate_to_pgvector_only
Revises: your_previous_revision_id
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'migrate_to_pgvector_only'
down_revision = 'your_previous_revision_id'  # Update this with your actual previous revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade to pgvector-only backend."""
    
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pgvector")
    
    # Create embeddings table for code vectors
    op.create_table(
        'code_embedding_vectors',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('document_id', sa.Integer, nullable=False, index=True),
        sa.Column('chunk_id', sa.Integer, nullable=True, index=True),
        sa.Column('project_id', sa.Integer, nullable=False, index=True),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('metadata', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create indexes for efficient querying
    op.create_index(
        'idx_code_emb_project_id', 
        'code_embedding_vectors', 
        ['project_id']
    )
    
    op.create_index(
        'idx_code_emb_document_id', 
        'code_embedding_vectors', 
        ['document_id']
    )
    
    # Create vector similarity index using IVFFlat
    # For small datasets (< 1M vectors), this provides good performance
    # For larger datasets, consider HNSW instead
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_code_emb_vector_ivfflat
        ON code_embedding_vectors
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )
    
    # Optional: Create knowledge embeddings table if implementing knowledge in pgvector
    op.create_table(
        'knowledge_embedding_vectors',
        sa.Column('id', sa.String(255), primary_key=True),  # UUID or knowledge entry ID
        sa.Column('project_id', sa.Integer, nullable=False, index=True),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('source', sa.String(500), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('source_type', sa.String(100), nullable=False, default='unknown'),
        sa.Column('metadata', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Indexes for knowledge embeddings
    op.create_index(
        'idx_knowledge_emb_project_id', 
        'knowledge_embedding_vectors', 
        ['project_id']
    )
    
    op.create_index(
        'idx_knowledge_emb_category', 
        'knowledge_embedding_vectors', 
        ['category']
    )
    
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_knowledge_emb_vector_ivfflat
        ON knowledge_embedding_vectors
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    """Downgrade from pgvector-only backend."""
    
    # Drop tables and indexes
    op.drop_table('knowledge_embedding_vectors')
    op.drop_table('code_embedding_vectors')
    
    # Note: We don't drop the pgvector extension as it might be used by other applications
    # If you want to drop it, uncomment the following line:
    # op.execute("DROP EXTENSION IF EXISTS pgvector")
