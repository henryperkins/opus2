"""add json defaults for chat messages

Revision ID: 005_add_json_defaults
Revises: 004_add_import_jobs
Create Date: 2025-06-24
"""

from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "005_add_json_defaults"
down_revision: Union[str, None] = "004_add_import_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:  # noqa: D401
    """Add default values for JSON columns in chat_messages table."""
    # Get connection for raw SQL execution
    conn = op.get_bind()

    # Update existing NULL values to empty arrays/objects
    conn.execute(text("UPDATE chat_messages SET code_snippets = '[]' WHERE code_snippets IS NULL"))
    conn.execute(text("UPDATE chat_messages SET referenced_files = '[]' WHERE referenced_files IS NULL"))
    conn.execute(text("UPDATE chat_messages SET referenced_chunks = '[]' WHERE referenced_chunks IS NULL"))
    conn.execute(text("UPDATE chat_messages SET applied_commands = '{}' WHERE applied_commands IS NULL"))

    # Set server defaults for future inserts
    op.alter_column('chat_messages', 'code_snippets',
                    existing_type=sa.JSON(),
                    server_default='[]')
    op.alter_column('chat_messages', 'referenced_files',
                    existing_type=sa.JSON(),
                    server_default='[]')
    op.alter_column('chat_messages', 'referenced_chunks',
                    existing_type=sa.JSON(),
                    server_default='[]')
    op.alter_column('chat_messages', 'applied_commands',
                    existing_type=sa.JSON(),
                    server_default='{}')


def downgrade() -> None:  # noqa: D401
    """Remove default values for JSON columns in chat_messages table."""
    # Remove server defaults
    op.alter_column('chat_messages', 'code_snippets',
                    existing_type=sa.JSON(),
                    server_default=None)
    op.alter_column('chat_messages', 'referenced_files',
                    existing_type=sa.JSON(),
                    server_default=None)
    op.alter_column('chat_messages', 'referenced_chunks',
                    existing_type=sa.JSON(),
                    server_default=None)
    op.alter_column('chat_messages', 'applied_commands',
                    existing_type=sa.JSON(),
                    server_default=None)
