"""
Fix runtime_config keys to be snake_case and unique.

Revision ID: 012
Revises: 011_add_user_feedback_system
Create Date: 2025-07-08 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011_add_user_feedback_system'
branch_labels = None
depends_on = None


def upgrade():
    # Create backup first
    op.execute("CREATE TABLE runtime_config_backup AS SELECT * FROM runtime_config")

    # Convert all camelCase keys to snake_case
    op.execute("""
        UPDATE runtime_config
        SET key = lower(regexp_replace(key, '([A-Z])', '_\1', 'g'))
        WHERE key ~ '[A-Z]'
    """)

    # Remove duplicate keys (keep the most recent)
    op.execute("""
        DELETE FROM runtime_config a
        USING runtime_config b
        WHERE a.id < b.id
        AND a.key = b.key
    """)

    # Add unique constraint if not exists
    try:
        op.create_unique_constraint('uq_runtime_config_key', 'runtime_config', ['key'])
    except Exception:
        # Constraint might already exist with a different name
        pass


def downgrade():
    op.drop_constraint('uq_runtime_config_key', 'runtime_config', type_='unique')
    # Restore from backup if needed
    op.execute("DELETE FROM runtime_config")
    op.execute("INSERT INTO runtime_config SELECT * FROM runtime_config_backup")
    op.execute("DROP TABLE runtime_config_backup")
