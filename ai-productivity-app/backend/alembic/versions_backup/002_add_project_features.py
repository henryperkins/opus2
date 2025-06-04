"""Add project features and timeline events

Revision ID: 002_add_project_features
Revises: 001_add_user_sessions
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '002_add_project_features'
down_revision = '001_add_user_sessions'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to projects table
    op.add_column('projects', sa.Column('color', sa.String(7), nullable=True))
    op.add_column('projects', sa.Column('emoji', sa.String(10), nullable=True))
    op.add_column('projects', sa.Column('tags', sa.JSON(), nullable=True))

    # Set default values for existing projects
    op.execute("UPDATE projects SET color = '#3B82F6' WHERE color IS NULL")
    op.execute("UPDATE projects SET emoji = '📁' WHERE emoji IS NULL")
    op.execute("UPDATE projects SET tags = '[]' WHERE tags IS NULL")

    # Create timeline_events table
    op.create_table('timeline_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_timeline_project', 'timeline_events', ['project_id'])
    op.create_index('idx_timeline_type', 'timeline_events', ['event_type'])
    op.create_index('idx_timeline_created', 'timeline_events', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_timeline_created', 'timeline_events')
    op.drop_index('idx_timeline_type', 'timeline_events')
    op.drop_index('idx_timeline_project', 'timeline_events')

    # Drop timeline_events table
    op.drop_table('timeline_events')

    # Remove columns from projects table
    op.drop_column('projects', 'tags')
    op.drop_column('projects', 'emoji')
    op.drop_column('projects', 'color')

