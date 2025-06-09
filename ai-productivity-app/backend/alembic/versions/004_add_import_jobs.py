"""add import_jobs table

Revision ID: 004_add_import_jobs
Revises: 003_add_search_history
Create Date: 2025-06-09
"""

from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_add_import_jobs"
down_revision: Union[str, None] = "003_add_search_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:  # noqa: D401
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("repo_url", sa.String(), nullable=False),
        sa.Column("branch", sa.String(), nullable=False, server_default="main"),
        sa.Column("commit_sha", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "cloning",
                "indexing",
                "embedding",
                "completed",
                "failed",
                name="importstatus",
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:  # noqa: D401
    op.drop_table("import_jobs")
