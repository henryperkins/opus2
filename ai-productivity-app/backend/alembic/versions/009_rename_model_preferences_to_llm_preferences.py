"""Rename model_preferences to llm_preferences in prompt_templates

Revision ID: 009_rename_model_preferences_to_llm_preferences
Revises: 008_add_prompt_templates
Create Date: 2025-06-26 07:18:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_rename_model_preferences_to_llm_preferences'
down_revision = '008_add_prompt_templates'
branch_labels = None
depends_on = None


def upgrade():
    """Rename model_preferences column to llm_preferences"""
    # Rename the column from model_preferences to llm_preferences
    op.alter_column(
        'prompt_templates',
        'model_preferences',
        new_column_name='llm_preferences',
        comment='LLM-specific preferences'
    )


def downgrade():
    """Rename llm_preferences column back to model_preferences"""
    # Rename the column back from llm_preferences to model_preferences
    op.alter_column(
        'prompt_templates',
        'llm_preferences',
        new_column_name='model_preferences',
        comment='Model-specific preferences'
    )
