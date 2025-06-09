"""add search history table

Revision ID: 003_add_search_history
Revises: None
Create Date: 2025-06-09
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_add_search_history"
down_revision = None  # The repo currently keeps versions in *versions_backup* only.
branch_labels = None
depends_on = None


def upgrade() -> None:  # noqa: D401
    op.create_table(
        "search_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query_text", sa.String(length=255), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("project_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_index(
        "idx_search_history_user_created",
        "search_history",
        ["user_id", "created_at"],
    )
    op.create_index("idx_search_history_query", "search_history", ["query_text"])


def downgrade() -> None:  # noqa: D401
    op.drop_index("idx_search_history_query", table_name="search_history")
    op.drop_index("idx_search_history_user_created", table_name="search_history")
    op.drop_table("search_history")
