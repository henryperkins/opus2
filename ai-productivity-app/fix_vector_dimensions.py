#!/usr/bin/env python3
"""Fix vector dimensions by dropping and recreating the embeddings table."""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.config import settings

def fix_vector_table():
    """Drop and recreate the vector table with correct dimensions."""
    # Parse database URL
    db_url = settings.database_url
    parsed = urlparse(db_url)
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],  # Remove leading /
        user=parsed.username,
        password=parsed.password,
        sslmode='require'
    )
    
    with conn:
        with conn.cursor() as cur:
            table_name = settings.postgres_vector_table
            vector_size = settings.embedding_vector_size
            
            print(f"Current vector size setting: {vector_size}")
            
            # Check if table exists and get its schema
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = 'embedding'
            """, (table_name,))
            
            result = cur.fetchone()
            if result:
                print(f"Found existing table {table_name} with embedding column: {result[1]}")
                
                # Drop the table to recreate with correct dimensions
                print(f"Dropping table {table_name}...")
                cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                
            # Create extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create table with correct vector size
            print(f"Creating table {table_name} with vector({vector_size})...")
            cur.execute(f"""
                CREATE TABLE {table_name} (
                    id           SERIAL PRIMARY KEY,
                    document_id  INTEGER      NOT NULL,
                    chunk_id     INTEGER,
                    project_id   INTEGER      NOT NULL,
                    embedding    vector({vector_size}) NOT NULL,
                    content      TEXT         NOT NULL,
                    content_hash TEXT         NOT NULL,
                    metadata     JSONB        NOT NULL,
                    created_at   TIMESTAMPTZ  DEFAULT NOW()
                )
            """)
            
            # Create indexes
            print("Creating indexes...")
            cur.execute(f"CREATE INDEX idx_{table_name}_project ON {table_name}(project_id)")
            
            # Create ivfflat index (should work now with 1536 dimensions)
            cur.execute(f"""
                CREATE INDEX idx_{table_name}_ivfflat 
                ON {table_name} 
                USING ivfflat (embedding vector_cosine_ops)
            """)
            
            print("Vector table recreated successfully!")
            print(f"Table: {table_name}")
            print(f"Vector dimensions: {vector_size}")
            print("Fast ANN indexing enabled with ivfflat")

if __name__ == "__main__":
    try:
        fix_vector_table()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)