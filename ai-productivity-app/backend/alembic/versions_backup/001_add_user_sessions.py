"""Add user sessions table and last_login column

Revision ID: 001_add_user_sessions
Revises:
Create Date: 2025-05-31 02:36:40.000000

"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_add_user_sessions"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:  # noqa: D401
    """Schema changes for Phase-2 auth"""
    # --- new table for active JWT / session tracking
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jti", sa.String(64), nullable=False, comment="JWT ID claim (unique per token)"),
        sa.Column("created_at", sa.DateTime, default=datetime.utcnow, nullable=False),
        sa.Column("revoked_at", sa.DateTime, nullable=True, comment="If not null token has been revoked"),
        sa.UniqueConstraint("jti", name="uq_sessions_jti"),
    )

    # --- add last_login to users table
    op.add_column("users", sa.Column("last_login", sa.DateTime, nullable=True))


def downgrade() -> None:  # noqa: D401
    """Rollback Phase-2 auth schema"""
    op.drop_column("users", "last_login")
    op.drop_table("sessions")
