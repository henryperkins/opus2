#!/usr/bin/env python3
"""
Automatically align the database schema with the current ORM models.

This script detects differences between the database schema and SQLAlchemy models,
providing a comprehensive report and options to automatically align them.

Features:
- Detects missing tables and columns
- Identifies extra columns in database not in models
- Reports type mismatches and constraint differences
- Handles nullable mismatches by recreating tables (SQLite)
- Handles type mismatches by recreating tables (SQLite)
- Supports dry-run mode to preview changes
- Handles indexes and foreign keys
- Interactive confirmation before applying changes
- Can drop extra tables and columns in force mode

Usage:
    python -m backend.scripts.auto_align_db [--dry-run] [--force]

Options:
    --dry-run: Show what would be changed without applying
    --force: Apply changes without confirmation and drop extra tables/columns
"""

import sys
import traceback
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import defaultdict

# Add the project root to the Python path to allow absolute imports
# This is needed to run the script standalone.
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent  # ai-productivity-app/backend/scripts -> ai-productivity-app
backend_dir = project_root / "backend"

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect, text, Column  # noqa: E402
from sqlalchemy.schema import CreateColumn, CreateTable  # noqa: E402
from sqlalchemy.types import TypeDecorator  # noqa: E402
from app.database import Base, engine  # noqa: E402

# Import specific model modules to register metadata without heavy side effects
from app.models import base, user, session, project, chat, code, embedding  # noqa: F401, E402
from app.models import timeline, search_history, import_job, config, prompt  # noqa: F401, E402


class SchemaAligner:
    """Handles database schema alignment with ORM models."""

    def __init__(self, dry_run: bool = False, force: bool = False):
        self.dry_run = dry_run
        self.force = force
        self.refresh_inspector()
        self.differences = defaultdict(list)
        # Track the current SQLAlchemy dialect (e.g. "sqlite", "postgresql")
        self.dialect_name = engine.dialect.name.lower()

    def refresh_inspector(self) -> None:
        """Refresh the inspector to get latest schema state."""
        self.inspector = inspect(engine)

    def get_db_columns(self, table_name: str) -> Dict[str, Dict]:
        """Fetches a dictionary of columns for a given table from the DB."""
        try:
            return {col["name"]: col for col in self.inspector.get_columns(table_name)}
        except Exception:
            # This can happen if the table does not exist yet
            return {}

    def get_db_indexes(self, table_name: str) -> List[Dict]:
        """Fetches indexes for a given table from the DB."""
        try:
            return self.inspector.get_indexes(table_name)
        except Exception:
            return []

    def get_db_foreign_keys(self, table_name: str) -> List[Dict]:
        """Fetches foreign keys for a given table from the DB."""
        try:
            return self.inspector.get_foreign_keys(table_name)
        except Exception:
            return []

    def get_column_type_string(self, column: Column) -> str:
        """Get a string representation of column type."""
        col_type = column.type
        if isinstance(col_type, TypeDecorator):
            col_type = col_type.impl
        return str(col_type)

    def compare_column_types(self, orm_column: Column, db_column: Dict) -> bool:
        """Compare ORM column type with database column type."""
        orm_type_str = self.get_column_type_string(orm_column).upper()
        db_type_str = str(db_column.get("type", "")).upper()

        # Extract base type without parameters for comparison
        orm_base = orm_type_str.split("(")[0].strip()
        db_base = db_type_str.split("(")[0].strip()

        # Handle exact matches first
        if orm_base == db_base:
            return True

        # Handle time zone variations
        if orm_base in ["DATETIME", "TIMESTAMP"] and db_base in ["TIMESTAMP", "TIMESTAMP WITHOUT TIME ZONE"]:
            return True
        if orm_base == "DATETIME" and db_base == "TIMESTAMP WITH TIME ZONE":
            return True

        # Handle JSON variants
        if orm_base in ["JSON", "JSONB"] and db_base in ["JSON", "JSONB"]:
            return True

        # Handle numeric types
        numeric_equivalents = {
            "DECIMAL": ["NUMERIC", "DECIMAL"],
            "NUMERIC": ["NUMERIC", "DECIMAL"],
            "FLOAT": ["DOUBLE PRECISION", "REAL", "FLOAT"],
            "DOUBLE PRECISION": ["DOUBLE PRECISION", "REAL", "FLOAT"],
            "REAL": ["DOUBLE PRECISION", "REAL", "FLOAT"],
        }

        if orm_base in numeric_equivalents:
            return db_base in numeric_equivalents[orm_base]

        # Handle string types
        if orm_base in ["STRING", "VARCHAR"] and db_base in ["VARCHAR", "CHARACTER VARYING"]:
            return True

        # Handle integer types
        if orm_base in ["INT", "INTEGER"] and db_base in ["INTEGER", "INT"]:
            return True

        # Handle boolean types
        if orm_base in ["BOOL", "BOOLEAN"] and db_base in ["BOOLEAN", "BOOL"]:
            return True

        # Handle enum types
        if "ENUM" in orm_base and "ENUM" in db_base:
            return True

        # If no special handling applies, they must match exactly
        return orm_base == db_base

    def get_default_value_for_type(self, column: Column) -> str:
        """Get appropriate default value for a column type to handle NULL values."""
        col_type = column.type
        if isinstance(col_type, TypeDecorator):
            col_type = col_type.impl

        type_str = str(col_type).upper()

        # Check if column has an explicit default
        if column.default is not None:
            if hasattr(column.default, 'arg'):
                # Handle server defaults
                default_val = column.default.arg
                if isinstance(default_val, str):
                    return f"'{default_val}'"
                return str(default_val)

        # PostgreSQL-specific type defaults
        if "BOOLEAN" in type_str or "BOOL" in type_str:
            return "FALSE"
        elif "JSONB" in type_str:
            # Smart JSONB defaults based on column name patterns
            if any(keyword in column.name.lower() for keyword in ["array", "list", "tags", "snippets", "files", "chunks"]):
                return "'[]'::jsonb"
            else:
                return "'{}'::jsonb"
        elif "JSON" in type_str:
            if any(keyword in column.name.lower() for keyword in ["array", "list", "tags", "snippets", "files", "chunks"]):
                return "'[]'"
            else:
                return "'{}'"
        elif "TSVECTOR" in type_str:
            return "to_tsvector('')"
        elif "UUID" in type_str:
            return "gen_random_uuid()"
        elif "INTEGER" in type_str or "INT" in type_str or "BIGINT" in type_str:
            return "0"
        elif "DECIMAL" in type_str or "NUMERIC" in type_str:
            return "0.0"
        elif "REAL" in type_str or "FLOAT" in type_str or "DOUBLE" in type_str:
            return "0.0"
        elif "TIMESTAMP" in type_str or "DATETIME" in type_str:
            return "CURRENT_TIMESTAMP"
        elif "VARCHAR" in type_str or "TEXT" in type_str or "STRING" in type_str:
            return "''"
        elif "ENUM" in type_str:
            # For enums, we'd need to inspect the enum values, default to first value
            return "NULL"  # Safer to use NULL for enums unless we can determine valid values
        else:
            # Fallback - use NULL for unknown types to avoid constraint violations
            return "NULL"

    def analyze_differences(self) -> None:
        """Analyze differences between database and ORM models."""
        print("🔍 Analyzing schema differences...")
        print("-" * 50)

        # Get all table names from both sources
        db_tables = set(self.inspector.get_table_names())
        orm_tables = set(Base.metadata.tables.keys())

        # Check for missing tables
        missing_tables = orm_tables - db_tables
        if missing_tables:
            self.differences["missing_tables"] = list(missing_tables)
            print(f"\n📋 Missing tables in database: {', '.join(missing_tables)}")

        # Check for extra tables
        extra_tables = db_tables - orm_tables
        if extra_tables:
            self.differences["extra_tables"] = list(extra_tables)
            print(f"\n📋 Extra tables in database (not in ORM): {', '.join(extra_tables)}")

        # Analyze each table that exists in both
        common_tables = db_tables & orm_tables
        for table_name in common_tables:
            table_diffs = self.analyze_table(table_name)
            if table_diffs:
                self.differences[table_name] = table_diffs

        if not any(self.differences.values()):
            print("\n✨ Database schema is perfectly aligned with ORM models!")
        else:
            print(f"\n📊 Found differences in {len(self.differences)} areas")

    def analyze_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Analyze differences for a specific table."""
        diffs = []
        orm_table = Base.metadata.tables[table_name]
        db_columns = self.get_db_columns(table_name)

        # Check columns
        orm_columns = {col.name: col for col in orm_table.columns}

        # Missing columns
        for col_name, orm_col in orm_columns.items():
            if col_name not in db_columns:
                diffs.append({
                    "type": "missing_column",
                    "column": col_name,
                    "details": (f"Type: {self.get_column_type_string(orm_col)}, "
                                f"Nullable: {orm_col.nullable}")
                })

        # Extra columns
        for col_name in db_columns:
            if col_name not in orm_columns:
                diffs.append({
                    "type": "extra_column",
                    "column": col_name,
                    "details": f"Type: {db_columns[col_name].get('type')}"
                })

        # Type mismatches
        for col_name in set(orm_columns.keys()) & set(db_columns.keys()):
            orm_col = orm_columns[col_name]
            db_col = db_columns[col_name]

            if not self.compare_column_types(orm_col, db_col):
                diffs.append({
                    "type": "type_mismatch",
                    "column": col_name,
                    "details": (f"ORM: {self.get_column_type_string(orm_col)}, "
                                f"DB: {db_col.get('type')}")
                })

            # Check nullable mismatch (skip primary keys to avoid noise)
            if (orm_col.nullable != db_col.get("nullable", True) and
                    not orm_col.primary_key):
                diffs.append({
                    "type": "nullable_mismatch",
                    "column": col_name,
                    "details": (f"ORM nullable: {orm_col.nullable}, "
                                f"DB nullable: {db_col.get('nullable', True)}")
                })

        # Detect server_default/validation mismatches
        server_default_mismatches = self.detect_server_default_mismatches(table_name)
        if server_default_mismatches:
            diffs.extend(server_default_mismatches)

        if diffs:
            print(f"\n🔧 Table '{table_name}':")
            for diff in diffs:
                icon = {
                    "missing_column": "➕",
                    "extra_column": "➖",
                    "type_mismatch": "🔄",
                    "nullable_mismatch": "❗",
                    "server_default_mismatch": "⚠️"
                }.get(diff["type"], "❓")
                print(f"   {icon} {diff['type']}: {diff['column']} - {diff['details']}")
                if "suggestion" in diff:
                    print(f"      💡 Suggestion: {diff['suggestion']}")

        return diffs

    def detect_server_default_mismatches(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Detect columns with server defaults that might cause None/validation issues.

        This identifies columns where:
        1. ORM has nullable=False but no Python default
        2. DB has a server_default
        3. This can cause validation errors when SQLAlchemy returns None before refresh

        Filters out common PostgreSQL patterns that are expected and safe.
        """
        mismatches = []
        orm_table = Base.metadata.tables[table_name]
        db_columns = self.get_db_columns(table_name)

        for col_name, orm_col in orm_table.columns.items():
            db_col = db_columns.get(col_name)
            if not db_col:
                continue

            # Check for potential server_default/validation issues
            has_server_default = hasattr(orm_col, 'server_default') and orm_col.server_default is not None
            has_python_default = hasattr(orm_col, 'default') and orm_col.default is not None

            if has_server_default and not orm_col.nullable and not has_python_default:
                # Filter out common PostgreSQL patterns that are safe
                server_default_str = str(orm_col.server_default.arg) if hasattr(orm_col.server_default, 'arg') else ""

                # Common safe patterns in PostgreSQL models
                safe_patterns = [
                    "now()",           # timestamp defaults
                    "CURRENT_TIMESTAMP",
                    "func.now()",
                    "gen_random_uuid()",  # UUID defaults
                    "TRUE",            # boolean defaults
                    "FALSE",
                    "'[]'",            # JSON array defaults
                    "'{}'",            # JSON object defaults
                    "0",               # numeric defaults
                ]

                # Skip columns with safe server defaults
                if any(pattern.lower() in server_default_str.lower() for pattern in safe_patterns):
                    continue

                # Skip timestamp columns (common pattern)
                if col_name.endswith(("_at", "_time")) and ("timestamp" in str(orm_col.type).lower() or "datetime" in str(orm_col.type).lower()):
                    continue

                mismatches.append({
                    "type": "server_default_mismatch",
                    "column": col_name,
                    "details": (
                        "Column has server_default but no Python default. "
                        "This can cause validation errors when SQLAlchemy "
                        "returns None before refresh. Consider adding "
                        "explicit Python default or refreshing after commit."
                    ),
                    "suggestion": f"Add explicit default like: {col_name}=True or db.refresh(instance)"
                })

        return mismatches

    def get_column_definition(self, column: Column) -> str:
        """Generate SQL for column definition."""
        return CreateColumn(column).compile(dialect=engine.dialect)

    def get_table_definition(self, table_name: str) -> str:
        """Generate SQL for table creation."""
        table = Base.metadata.tables[table_name]
        create_table_sql = CreateTable(table).compile(dialect=engine.dialect)

        # Fix SQLite compatibility issues
        sql_str = str(create_table_sql)

        # Dialect-specific clean-ups (only needed for SQLite)
        if self.dialect_name == "sqlite":
            # Remove PostgreSQL-specific syntax that SQLite doesn't understand
            sql_str = sql_str.replace(" DEFAULT '[]'::jsonb", " DEFAULT '[]'")
            sql_str = sql_str.replace(" DEFAULT '{}'::jsonb", " DEFAULT '{}'")
            sql_str = sql_str.replace("::jsonb", "")

        return sql_str

    def build_column_recreation_sql(self, table_name: str, orm_table) -> List[Tuple[str, str]]:
        """
        SQLite cannot ALTER COLUMN, so we:
          1. create _new table with desired schema
          2. copy data with COALESCE for NULL handling
          3. drop old table
          4. rename new → old
        """
        # Generate the CREATE TABLE statement for the new table with proper SQLite syntax
        new_table_name = f"{table_name}__new"
        new_table_sql = self.get_table_definition(table_name).replace(
            f"CREATE TABLE {table_name}",
            f"CREATE TABLE {new_table_name}"
        )

        # Get column names for data copying
        db_columns = self.get_db_columns(table_name)
        orm_columns = {col.name: col for col in orm_table.columns}
        common_columns = set(orm_columns.keys()) & set(db_columns.keys())

        # Build the SELECT statement with COALESCE for nullable mismatches
        select_parts = []
        for col_name in sorted(common_columns):
            orm_col = orm_columns[col_name]
            db_col = db_columns[col_name]

            # Check if this column has nullable mismatch (DB allows NULL, ORM doesn't)
            if db_col.get("nullable", True) and not orm_col.nullable:
                # Provide appropriate default value based on column type
                default_value = self.get_default_value_for_type(orm_col)
                select_parts.append(f"COALESCE({col_name}, {default_value}) AS {col_name}")
            else:
                select_parts.append(col_name)

        select_clause = ", ".join(select_parts)
        copy_cols = ", ".join(sorted(common_columns))

        return [
            ("create_temp", new_table_sql),
            ("copy_data", f'INSERT INTO "{new_table_name}" ({copy_cols}) SELECT {select_clause} FROM "{table_name}";'),
            ("drop_old", f'DROP TABLE "{table_name}";'),
            ("rename", f'ALTER TABLE "{new_table_name}" RENAME TO "{table_name}";')
        ]

    def generate_alignment_sql(self) -> List[Tuple[str, str]]:
        """Generate SQL statements to align the database."""
        sql_statements = []

        # Create missing tables
        if "missing_tables" in self.differences:
            for table_name in self.differences["missing_tables"]:
                sql = str(self.get_table_definition(table_name))
                sql_statements.append(("create_table", sql))

        # Drop extra tables if in force mode
        if "extra_tables" in self.differences and self.force:
            for table_name in self.differences["extra_tables"]:
                sql_statements.append(("drop_table", f'DROP TABLE "{table_name}";'))

        # Handle table-specific differences
        for table_name, diffs in self.differences.items():
            if table_name in ["missing_tables", "extra_tables"]:
                continue

            orm_table = Base.metadata.tables[table_name]

            # Determine whether we must recreate (only for SQLite)
            needs_recreation = self.dialect_name == "sqlite" and any(
                diff["type"] in ["type_mismatch", "nullable_mismatch"] for diff in diffs
            )

            if needs_recreation:
                # SQLite: recreate table via the table-rebuild pattern
                sql_statements.extend(
                    self.build_column_recreation_sql(table_name, orm_table)
                )
            else:
                # Non-SQLite (e.g. PostgreSQL) – generate ALTER statements
                for diff in diffs:
                    if diff["type"] == "missing_column":
                        column = next(c for c in orm_table.columns if c.name == diff["column"])
                        col_def = self.get_column_definition(column)
                        sql = f'ALTER TABLE "{table_name}" ADD COLUMN {col_def}'
                        sql_statements.append(("add_column", sql))

                    elif diff["type"] == "extra_column" and self.force:
                        sql = f'ALTER TABLE "{table_name}" DROP COLUMN "{diff["column"]}"'
                        sql_statements.append(("drop_column", sql))

                    elif diff["type"] == "type_mismatch":
                        column = orm_table.columns[diff["column"]]
                        new_type_sql = column.type.compile(dialect=engine.dialect)
                        sql = (
                            f'ALTER TABLE "{table_name}" ALTER COLUMN "{column.name}" '
                            f'TYPE {new_type_sql} USING "{column.name}"::{new_type_sql};'
                        )
                        sql_statements.append(("alter_column_type", sql))

                    elif diff["type"] == "nullable_mismatch":
                        column = orm_table.columns[diff["column"]]
                        if column.nullable:
                            sql = f'ALTER TABLE "{table_name}" ALTER COLUMN "{column.name}" DROP NOT NULL;'
                            sql_statements.append(("drop_not_null", sql))
                        else:
                            sql = f'ALTER TABLE "{table_name}" ALTER COLUMN "{column.name}" SET NOT NULL;'
                            sql_statements.append(("set_not_null", sql))

        return sql_statements

    def apply_changes(self, sql_statements: List[Tuple[str, str]]) -> bool:
        """Apply the SQL statements to align the database."""
        if not sql_statements:
            print("\n✨ No changes needed!")
            return True

        print(f"\n📝 {len(sql_statements)} SQL statements to execute:")
        print("-" * 50)

        for i, (action, sql) in enumerate(sql_statements, 1):
            print(f"\n{i}. [{action}]")
            print(f"   {sql}")

        if self.dry_run:
            print("\n🔍 DRY RUN: No changes were applied.")
            return True

        if not self.force:
            # Check if we're in a non-interactive environment
            import os
            if not os.isatty(0):  # stdin is not a TTY
                print("❌ Running in non-interactive environment without --force flag.")
                print("   Use --force to apply changes automatically.")
                return False

            response = input("\n⚠️  Apply these changes? (yes/no): ").lower().strip()
            if response != "yes":
                print("❌ Aborted. No changes were made.")
                return False

        print("\n🚀 Applying changes...")
        errors = []
        statements_executed = 0

        try:
            with engine.connect() as connection:
                # Execute each statement individually with proper error handling
                for i, (action, sql) in enumerate(sql_statements):
                    try:
                        print(f"\n🔄 Executing {action}: {sql[:100]}{'...' if len(sql) > 100 else ''}")

                        # Execute in transaction
                        with connection.begin() as trans:
                            result = connection.execute(text(sql))
                            trans.commit()

                        statements_executed += 1
                        print(f"✅ {action}: SUCCESS")

                        # Log any result info
                        if hasattr(result, 'rowcount') and result.rowcount is not None:
                            print(f"   Rows affected: {result.rowcount}")

                    except Exception as e:
                        error_msg = f"❌ {action} failed: {str(e)}"
                        print(error_msg)
                        errors.append(f"{action}: {str(e)}")

                        # For debugging, show the full SQL that failed
                        print(f"   Failed SQL: {sql}")

                        # Continue with other statements unless it's a critical failure
                        if "does not exist" in str(e).lower() and action in ["add_column", "alter_column_type"]:
                            print(f"   ⚠️  Skipping {action} - table may not exist yet")
                            continue

        except Exception as e:
            error_msg = f"❌ Connection error: {str(e)}"
            print(error_msg)
            errors.append(error_msg)

        print("\n📊 Execution Summary:")
        print(f"   Statements executed: {statements_executed}/{len(sql_statements)}")
        print(f"   Errors encountered: {len(errors)}")

        if errors:
            print(f"\n⚠️  Completed with {len(errors)} errors:")
            for error in errors:
                print(f"   • {error}")
            return False
        else:
            print("\n✅ All changes applied successfully!")
            # Refresh inspector after successful changes
            print("🔄 Refreshing database schema...")
            self.refresh_inspector()
            return True

    def run(self) -> bool:
        """Run the complete alignment process."""
        try:
            print("🔧 Database Schema Alignment Tool")
            print(f"📁 Database URL: {engine.url}")
            print(f"🗄️  Dialect: {self.dialect_name}")
            print("-" * 50)

            # First ensure all tables exist
            if not self.dry_run:
                print("📋 Creating any missing tables...")
                try:
                    Base.metadata.create_all(bind=engine)
                    print("✅ Base metadata tables created/verified")
                except Exception as e:
                    print(f"⚠️  Warning during table creation: {e}")

                # Refresh inspector after DDL changes
                print("🔄 Refreshing inspector after table creation...")
                self.refresh_inspector()

            # Analyze differences
            print("\n🔍 Analyzing schema differences...")
            self.analyze_differences()

            # Generate and apply SQL
            print("\n🛠️  Generating alignment SQL...")
            sql_statements = self.generate_alignment_sql()

            if sql_statements:
                print(f"📝 Generated {len(sql_statements)} SQL statements")
            else:
                print("✨ No SQL statements needed - schema is aligned!")

            return self.apply_changes(sql_statements)

        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}", file=sys.stderr)
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Align database schema with ORM models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without applying"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Apply changes without confirmation prompt and drop extra tables/columns"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debugging output"
    )

    args = parser.parse_args()

    print("🔧 Database Schema Alignment Tool")
    print(f"📁 Running from: {__file__}")
    print("-" * 50)

    if args.dry_run:
        print("🔍 Running in DRY RUN mode - no changes will be made")
    if args.force:
        print("⚡ Running in FORCE mode - changes will be applied without confirmation")
    if args.debug:
        print("🐛 Debug mode enabled - verbose output")

    # Test database connection first
    print("🔗 Testing database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to: {version}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

    aligner = SchemaAligner(dry_run=args.dry_run, force=args.force)
    success = aligner.run()

    print("-" * 50)
    if success:
        print("🎉 Database alignment completed successfully!")
        if not args.dry_run:
            print("💡 Run the script again to verify no differences remain")
    else:
        print("❌ Database alignment completed with issues.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
