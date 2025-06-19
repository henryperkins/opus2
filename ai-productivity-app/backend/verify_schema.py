#!/usr/bin/env python3
"""Comprehensive database schema verification."""

import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def verify_schema():
    """Verify database schema matches ORM models in detail."""
    from app.database import engine
    from sqlalchemy import text, inspect

    inspector = inspect(engine)

    print("🔍 Detailed schema verification...")

    # Define expected schema for key tables
    expected_schemas = {
        'projects': {
            'columns': {
                'id', 'title', 'description', 'status', 'owner_id',
                'color', 'emoji', 'tags', 'created_at', 'updated_at'
            },
            'foreign_keys': ['owner_id']
        },
        'chat_sessions': {
            'columns': {
                'id', 'project_id', 'title', 'is_active', 'summary',
                'summary_updated_at', 'created_at', 'updated_at'
            },
            'foreign_keys': ['project_id']
        },
        'chat_messages': {
            'columns': {
                'id', 'session_id', 'user_id', 'role', 'content',
                'code_snippets', 'referenced_files', 'referenced_chunks',
                'applied_commands', 'is_edited', 'edited_at',
                'original_content', 'is_deleted', 'created_at', 'updated_at'
            },
            'foreign_keys': ['session_id', 'user_id']
        },
        'timeline_events': {
            'columns': {
                'id', 'project_id', 'event_type', 'title', 'description',
                'metadata', 'user_id', 'created_at', 'updated_at'
            },
            'foreign_keys': ['project_id', 'user_id']
        },
        'import_jobs': {
            'columns': {
                'id', 'project_id', 'requested_by', 'repo_url', 'branch',
                'commit_sha', 'status', 'progress_pct', 'error',
                'created_at', 'updated_at'
            },
            'foreign_keys': ['project_id', 'requested_by']
        }
    }

    issues = []

    for table_name, expected in expected_schemas.items():
        try:
            # Check if table exists
            if not inspector.has_table(table_name):
                issues.append(f"❌ Table '{table_name}' missing")
                continue

            # Get actual columns
            actual_columns = {col['name'] for col in inspector.get_columns(table_name)}
            expected_columns = expected['columns']

            # Check for missing columns
            missing_columns = expected_columns - actual_columns
            if missing_columns:
                issues.append(f"❌ Table '{table_name}' missing columns: {missing_columns}")

            # Check for extra columns (just warn, not an error)
            extra_columns = actual_columns - expected_columns
            if extra_columns:
                print(f"⚠️  Table '{table_name}' has extra columns: {extra_columns}")

            # Check foreign keys
            actual_fks = inspector.get_foreign_keys(table_name)
            actual_fk_columns = {fk['constrained_columns'][0] for fk in actual_fks if fk['constrained_columns']}
            expected_fk_columns = set(expected['foreign_keys'])

            missing_fks = expected_fk_columns - actual_fk_columns
            if missing_fks:
                issues.append(f"❌ Table '{table_name}' missing foreign keys: {missing_fks}")

            if not missing_columns and not missing_fks:
                print(f"✅ Table '{table_name}' schema correct")

        except Exception as e:
            issues.append(f"❌ Error checking table '{table_name}': {e}")

    if issues:
        print("\n" + "\n".join(issues))
        return False
    else:
        print("✅ All table schemas match ORM models")
        return True


if __name__ == "__main__":
    success = verify_schema()
    sys.exit(0 if success else 1)
