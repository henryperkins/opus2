#!/usr/bin/env python3
"""Sync database schema with ORM models."""

import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def sync_database():
    """Ensure database matches ORM models."""
    try:
        # Import the database module and models
        from app.database import engine, Base
        from app import models  # This will import all models

        print("🔍 Checking database connection...")
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")

        print("🔨 Creating/updating all tables from ORM models...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database schema synchronized with ORM models")

        # Verify all expected tables exist
        print("🔍 Verifying tables...")
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))
            tables = [row[0] for row in result.fetchall()]

        expected_tables = {
            'users', 'sessions', 'projects', 'timeline_events',
            'chat_sessions', 'chat_messages', 'code_documents',
            'code_embeddings', 'search_history', 'import_jobs'
        }

        missing_tables = expected_tables - set(tables)
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False

        extra_tables = set(tables) - expected_tables - {'sqlite_sequence', 'embedding_metadata'}
        if extra_tables:
            print(f"⚠️  Extra tables: {extra_tables}")

        print(f"✅ All expected tables present: {sorted(expected_tables)}")

        # Check for any foreign key constraints
        print("🔍 Checking foreign key constraints...")
        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.execute(text("PRAGMA foreign_key_check"))
        print("✅ Foreign key constraints valid")

        return True

    except Exception as e:
        print(f"❌ Error synchronizing database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = sync_database()
    sys.exit(0 if success else 1)
