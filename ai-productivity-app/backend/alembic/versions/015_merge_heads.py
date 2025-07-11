"""Merge parallel heads into a single lineage

Revision ID: 015_merge_heads
Revises: 014_fix_capabilities_default, add_provider_model_config
Create Date: 2025-07-11 00:00:00
"""

# NOTE: This migration has **no schema changes**.  It merely tells Alembic
# that the two previously diverging branches – ``014_fix_capabilities_default``
# and ``add_provider_model_config`` – have been *logically* merged so future
# upgrades have a single linear head revision.

from alembic import op  # noqa: F401 – imported for Alembic env


# Revision identifiers, used by Alembic.
revision = "015_merge_heads"
down_revision = (
    "014_fix_capabilities_default",
    "add_provider_model_config",
)
branch_labels = None
depends_on = None


def upgrade() -> None:  # noqa: D401 – Alembic signature
    """No-op merge revision."""
    pass


def downgrade() -> None:  # noqa: D401 – Alembic signature
    """Downgrade simply re-creates the previous divergence (no-op)."""
    pass
