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
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect, text, Column  # noqa: E402
from sqlalchemy.schema import CreateColumn, CreateTable  # noqa: E402
from sqlalchemy.types import TypeDecorator  # noqa: E402
from app.database import Base, engine  # noqa: E402
# The following import is necessary to ensure all model classes are registered
# with SQLAlchemy's metadata before we attempt to create or align them.
from app import models  # noqa: F401, E402


class SchemaAligner:
    """Handles database schema alignment with ORM models."""

    def __init__(self, dry_run: bool = False, force: bool = False):
        self.dry_run = dry_run
        self.force = force
        self.inspector = inspect(engine)
        self.differences = defaultdict(list)

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

        # Normalize common type variations
        type_mappings = {
            "VARCHAR": "VARCHAR",
            "STRING": "VARCHAR",
            "TEXT": "TEXT",
            "INTEGER": "INTEGER",
            "INT": "INTEGER",
            "BOOLEAN": "BOOLEAN",
            "BOOL": "BOOLEAN",
            "DATETIME": "DATETIME",
            "TIMESTAMP": "DATETIME",
            "JSON": "JSON",
            "JSONB": "JSON"
        }

        # Extract base type without parameters
        orm_base = orm_type_str.split("(")[0]
        db_base = db_type_str.split("(")[0]

        orm_normalized = type_mappings.get(orm_base, orm_base)
        db_normalized = type_mappings.get(db_base, db_base)

        return orm_normalized == db_normalized

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

        # Provide type-appropriate defaults for common types
        if "BOOLEAN" in type_str or "BOOL" in type_str:
            return "FALSE"
        elif "JSON" in type_str:
            if "referenced" in column.name.lower() or "code_snippets" in column.name.lower():
                return "'[]'"
            else:
                return "'{}'"
        elif "INTEGER" in type_str or "INT" in type_str:
            return "0"
        elif "VARCHAR" in type_str or "TEXT" in type_str or "STRING" in type_str:
            return "''"
        else:
            # Fallback - use empty string for most cases
            return "''"

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

            # Check nullable mismatch
            if orm_col.nullable != db_col.get("nullable", True):
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

        # Remove PostgreSQL-specific syntax that SQLite doesn't understand
        # Handle the jsonb casting syntax properly
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
            ("copy_data", f"INSERT INTO {new_table_name} ({copy_cols}) SELECT {select_clause} FROM {table_name};"),
            ("drop_old", f"DROP TABLE {table_name};"),
            ("rename", f"ALTER TABLE {new_table_name} RENAME TO {table_name};")
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
                sql_statements.append(("drop_table", f"DROP TABLE {table_name};"))

        # Handle table-specific differences
        for table_name, diffs in self.differences.items():
            if table_name in ["missing_tables", "extra_tables"]:
                continue

            orm_table = Base.metadata.tables[table_name]

            # Check if we need to recreate the table for type/nullable changes
            needs_recreation = any(diff["type"] in ["type_mismatch", "nullable_mismatch"] for diff in diffs)

            if needs_recreation:
                # SQLite: need to recreate table via table-rebuild for type/nullable changes
                sql_statements.extend(
                    self.build_column_recreation_sql(table_name, orm_table)
                )
            else:
                # Handle individual column changes that don't require recreation
                for diff in diffs:
                    if diff["type"] == "missing_column":
                        column = next(c for c in orm_table.columns if c.name == diff["column"])
                        col_def = self.get_column_definition(column)
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_def}"
                        sql_statements.append(("add_column", sql))

                    elif diff["type"] == "extra_column" and self.force:
                        # Only drop columns in force mode
                        sql = f"ALTER TABLE {table_name} DROP COLUMN {diff['column']}"
                        sql_statements.append(("drop_column", sql))

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
            response = input("\n⚠️  Apply these changes? (yes/no): ").lower().strip()
            if response != "yes":
                print("❌ Aborted. No changes were made.")
                return False

        print("\n🚀 Applying changes...")
        errors = []

        with engine.connect() as connection:
            # Group related operations (like table recreation) into transactions
            current_transaction = []

            for i, (action, sql) in enumerate(sql_statements):
                current_transaction.append((action, sql))
                # Check if this is the end of a multi-step operation or the last statement
                is_last_statement = i == len(sql_statements) - 1
                is_end_of_recreation = (action == "rename" or (
                    i + 1 < len(sql_statements) and sql_statements[i + 1][0] == "create_temp"
                ))

                if is_last_statement or is_end_of_recreation or action not in ["create_temp", "copy_data", "drop_old", "rename"]:
                    # Execute the current transaction
                    try:
                        with connection.begin():
                            for trans_action, trans_sql in current_transaction:
                                connection.execute(text(trans_sql))
                                print(f"✅ {trans_action}: Success")
                        current_transaction = []
                    except Exception as e:
                        error_msg = f"❌ Transaction failed: {str(e)}"
                        print(error_msg)
                        errors.append(error_msg)
                        current_transaction = []

        if errors:
            print(f"\n⚠️  Completed with {len(errors)} errors")
            return False
        else:
            print("\n✅ All changes applied successfully!")
            return True

    def run(self) -> bool:
        """Run the complete alignment process."""
        try:
            # First ensure all tables exist
            if not self.dry_run:
                print("📋 Creating any missing tables...")
                Base.metadata.create_all(bind=engine)

            # Analyze differences
            self.analyze_differences()

            # Generate and apply SQL
            sql_statements = self.generate_alignment_sql()
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

    args = parser.parse_args()

    print("🔧 Database Schema Alignment Tool")
    print(f"📁 Running from: {__file__}")
    print(f"🗄️  Database: {engine.url}")
    print("-" * 50)

    if args.dry_run:
        print("🔍 Running in DRY RUN mode - no changes will be made")
    if args.force:
        print("⚡ Running in FORCE mode - changes will be applied without confirmation")

    aligner = SchemaAligner(dry_run=args.dry_run, force=args.force)
    success = aligner.run()

    print("-" * 50)
    if success:
        print("🎉 Database alignment completed successfully!")
    else:
        print("❌ Database alignment completed with issues.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
