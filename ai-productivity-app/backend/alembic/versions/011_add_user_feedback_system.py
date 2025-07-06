"""Add user feedback system

Revision ID: 011_add_user_feedback_system
Revises: 010_add_patterns_to_import_jobs
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_add_user_feedback_system'
down_revision = '010_add_patterns_to_import_jobs'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_feedback table
    op.create_table(
        'user_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('helpful', sa.Boolean(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('accuracy_rating', sa.Integer(), nullable=True),
        sa.Column('clarity_rating', sa.Integer(), nullable=True),
        sa.Column('completeness_rating', sa.Integer(), nullable=True),
        sa.Column('response_length', sa.Integer(), nullable=True),
        sa.Column('had_code_examples', sa.Boolean(), default=False),
        sa.Column('had_citations', sa.Boolean(), default=False),
        sa.Column('rag_was_used', sa.Boolean(), default=False),
        sa.Column('rag_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for user_feedback
    op.create_index('ix_user_feedback_message_id', 'user_feedback', ['message_id'])
    op.create_index('ix_user_feedback_user_id', 'user_feedback', ['user_id'])
    op.create_index('ix_user_feedback_session_id', 'user_feedback', ['session_id'])
    op.create_index('ix_user_feedback_created_at', 'user_feedback', ['created_at'])
    op.create_index('ix_user_feedback_rating', 'user_feedback', ['rating'])
    op.create_index('ix_user_feedback_helpful', 'user_feedback', ['helpful'])
    
    # Create feedback_summaries table
    op.create_table(
        'feedback_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('total_feedback_count', sa.Integer(), default=0),
        sa.Column('average_rating', sa.Float(), nullable=True),
        sa.Column('helpful_percentage', sa.Float(), nullable=True),
        sa.Column('avg_accuracy', sa.Float(), nullable=True),
        sa.Column('avg_clarity', sa.Float(), nullable=True),
        sa.Column('avg_completeness', sa.Float(), nullable=True),
        sa.Column('rag_responses_count', sa.Integer(), default=0),
        sa.Column('rag_avg_confidence', sa.Float(), nullable=True),
        sa.Column('rag_success_rate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for feedback_summaries
    op.create_index('ix_feedback_summaries_period_type', 'feedback_summaries', ['period_type'])
    op.create_index('ix_feedback_summaries_period_start', 'feedback_summaries', ['period_start'])
    op.create_index('ix_feedback_summaries_period_end', 'feedback_summaries', ['period_end'])


def downgrade():
    # Drop feedback_summaries table
    op.drop_index('ix_feedback_summaries_period_end', 'feedback_summaries')
    op.drop_index('ix_feedback_summaries_period_start', 'feedback_summaries')
    op.drop_index('ix_feedback_summaries_period_type', 'feedback_summaries')
    op.drop_table('feedback_summaries')
    
    # Drop user_feedback table
    op.drop_index('ix_user_feedback_helpful', 'user_feedback')
    op.drop_index('ix_user_feedback_rating', 'user_feedback')
    op.drop_index('ix_user_feedback_created_at', 'user_feedback')
    op.drop_index('ix_user_feedback_session_id', 'user_feedback')
    op.drop_index('ix_user_feedback_user_id', 'user_feedback')
    op.drop_index('ix_user_feedback_message_id', 'user_feedback')
    op.drop_table('user_feedback')