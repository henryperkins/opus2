"""Fix capabilities column default to '{}'::jsonb and normalize data

Revision ID: 014_fix_capabilities_default
Revises: 013_populate_model_configurations
Create Date: 2025-07-10 21:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = "014_fix_capabilities_default"
down_revision = "013_populate_model_configurations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change default to JSON object and normalize existing rows."""
    # Set new server default on the column
    op.alter_column(
        "model_configurations",
        "capabilities",
        server_default=sa.text("'{}'::jsonb"),
        existing_type=sa.dialects.postgresql.JSONB(),
        nullable=False,
    )

    # Convert any legacy array values (e.g. '[]') to empty JSON objects
    op.execute(
        text(
            """
            UPDATE model_configurations
            SET capabilities = '{}'::jsonb
            WHERE jsonb_typeof(capabilities) = 'array'
            """
        )
    )


def downgrade() -> None:
    """Revert default back to empty JSON array (legacy)."""
    op.alter_column(
        "model_configurations",
        "capabilities",
        server_default=sa.text("'[]'::jsonb"),
        existing_type=sa.dialects.postgresql.JSONB(),
        nullable=False,
    )
