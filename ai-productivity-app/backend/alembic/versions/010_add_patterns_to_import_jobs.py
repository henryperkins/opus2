"""add include/exclude patterns to import_jobs

Revision ID: 010_add_patterns_to_import_jobs
Revises: 009_rename_model_preferences_to_llm_preferences
Create Date: 2025-07-06
"""

from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "010_add_patterns_to_import_jobs"
down_revision: Union[str, None] = "009_rename_model_preferences_to_llm_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:  # noqa: D401
    """Add include_patterns and exclude_patterns columns to import_jobs table."""
    op.add_column("import_jobs", sa.Column("include_patterns", sa.JSON(), nullable=True))
    op.add_column("import_jobs", sa.Column("exclude_patterns", sa.JSON(), nullable=True))


def downgrade() -> None:  # noqa: D401
    """Remove include_patterns and exclude_patterns columns from import_jobs table."""
    op.drop_column("import_jobs", "exclude_patterns")
    op.drop_column("import_jobs", "include_patterns")