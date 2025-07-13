"""Add latest AI models from OpenAI, Azure, and Anthropic

Revision ID: 016_add_latest_ai_models
Revises: 015_add_provider_model_config
Create Date: 2025-01-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '016_add_latest_ai_models'
down_revision = '015_add_provider_model_config'
branch_labels = None
depends_on = None


def upgrade():
    # Create a reference to the model_configurations table
    model_configurations = table('model_configurations',
        column('model_id', sa.String),
        column('name', sa.String),
        column('provider', sa.String),
        column('model_family', sa.String),
        column('context_window', sa.Integer),
        column('max_output_tokens', sa.Integer),
        column('capabilities', sa.JSON),
        column('cost_input_per_1k', sa.Float),
        column('cost_output_per_1k', sa.Float),
        column('avg_response_time_ms', sa.Integer),
        column('is_available', sa.Boolean),
        column('is_deprecated', sa.Boolean),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime)
    )
    
    # Insert new models using raw SQL for better control
    op.execute("""
        INSERT INTO model_configurations (
            model_id, name, provider, model_family, context_window, max_output_tokens,
            capabilities, cost_input_per_1k, cost_output_per_1k, avg_response_time_ms,
            is_available, is_deprecated, created_at, updated_at
        ) VALUES 
        -- Azure OpenAI o-series reasoning models
        ('o3', 'OpenAI o3', 'azure', 'o-series', 200000, 100000,
         '{"reasoning": true, "vision": true, "function_calling": true, "json_mode": true, "streaming": true, "tool_use": true, "reasoning_effort_control": true}',
         0.015, 0.060, 3000, true, false, NOW(), NOW()),
        
        ('o4-mini', 'OpenAI o4-mini', 'azure', 'o-series', 200000, 100000,
         '{"reasoning": true, "vision": true, "function_calling": true, "json_mode": true, "streaming": true, "tool_use": true, "reasoning_effort_control": true}',
         0.003, 0.012, 1500, true, false, NOW(), NOW()),
        
        ('o3-mini', 'OpenAI o3-mini', 'azure', 'o-series', 200000, 100000,
         '{"reasoning": true, "function_calling": true, "json_mode": true, "streaming": true, "tool_use": true, "reasoning_effort_control": true}',
         0.002, 0.008, 1200, true, false, NOW(), NOW()),
        
        -- OpenAI models (same as Azure for API compatibility)
        ('o3', 'OpenAI o3', 'openai', 'o-series', 200000, 100000,
         '{"reasoning": true, "vision": true, "function_calling": true, "json_mode": true, "streaming": true, "tool_use": true, "reasoning_effort_control": true}',
         0.015, 0.060, 3000, true, false, NOW(), NOW()),
        
        ('o4-mini', 'OpenAI o4-mini', 'openai', 'o-series', 200000, 100000,
         '{"reasoning": true, "vision": true, "function_calling": true, "json_mode": true, "streaming": true, "tool_use": true, "reasoning_effort_control": true}',
         0.003, 0.012, 1500, true, false, NOW(), NOW()),
        
        -- Anthropic Claude 4 models
        ('claude-opus-4-20250514', 'Claude Opus 4', 'anthropic', 'claude-4', 200000, 32000,
         '{"vision": true, "function_calling": true, "json_mode": true, "streaming": true, "tool_use": true, "extended_thinking": true, "interleaved_thinking": true, "memory_files": true}',
         0.015, 0.075, 3500, true, false, NOW(), NOW()),
        
        ('claude-sonnet-4-20250522', 'Claude Sonnet 4', 'anthropic', 'claude-4', 200000, 64000,
         '{"vision": true, "function_calling": true, "json_mode": true, "streaming": true, "tool_use": true, "extended_thinking": true, "interleaved_thinking": true}',
         0.003, 0.015, 1800, true, false, NOW(), NOW()),
        
        ('claude-3-5-haiku-20241022', 'Claude 3.5 Haiku', 'anthropic', 'claude-3', 200000, 8000,
         '{"vision": true, "function_calling": true, "json_mode": true, "streaming": true, "tool_use": true}',
         0.001, 0.005, 800, true, false, NOW(), NOW())
        
        ON CONFLICT (model_id, provider) DO UPDATE SET
            name = EXCLUDED.name,
            model_family = EXCLUDED.model_family,
            context_window = EXCLUDED.context_window,
            max_output_tokens = EXCLUDED.max_output_tokens,
            capabilities = EXCLUDED.capabilities,
            cost_input_per_1k = EXCLUDED.cost_input_per_1k,
            cost_output_per_1k = EXCLUDED.cost_output_per_1k,
            avg_response_time_ms = EXCLUDED.avg_response_time_ms,
            is_available = EXCLUDED.is_available,
            is_deprecated = EXCLUDED.is_deprecated,
            updated_at = NOW();
    """)
    
    # Update gpt-4.1 model with new 1M context window
    op.execute("""
        INSERT INTO model_configurations (
            model_id, name, provider, model_family, context_window, max_output_tokens,
            capabilities, cost_input_per_1k, cost_output_per_1k, avg_response_time_ms,
            is_available, is_deprecated, created_at, updated_at
        ) VALUES 
        ('gpt-4.1', 'GPT-4.1', 'azure', 'gpt-4', 1000000, 16384,
         '{"vision": true, "function_calling": true, "json_mode": true, "streaming": true, "tool_use": true}',
         0.010, 0.030, 2000, true, false, NOW(), NOW())
        
        ON CONFLICT (model_id, provider) DO UPDATE SET
            context_window = EXCLUDED.context_window,
            max_output_tokens = EXCLUDED.max_output_tokens,
            cost_input_per_1k = EXCLUDED.cost_input_per_1k,
            cost_output_per_1k = EXCLUDED.cost_output_per_1k,
            updated_at = NOW();
    """)
    
    # Update any existing models that should be marked as deprecated
    op.execute("""
        UPDATE model_configurations 
        SET is_deprecated = TRUE, updated_at = NOW()
        WHERE model_id IN ('claude-3-opus-20240229', 'claude-3-haiku-20240307')
        AND provider = 'anthropic';
    """)


def downgrade():
    # Remove the newly added models
    op.execute("""
        DELETE FROM model_configurations 
        WHERE (model_id, provider) IN (
            ('o3', 'azure'), ('o3', 'openai'),
            ('o4-mini', 'azure'), ('o4-mini', 'openai'),
            ('o3-mini', 'azure'),
            ('claude-opus-4-20250514', 'anthropic'), 
            ('claude-sonnet-4-20250522', 'anthropic'), 
            ('claude-3-5-haiku-20241022', 'anthropic')
        );
    """)
    
    # Restore deprecated status if needed
    op.execute("""
        UPDATE model_configurations 
        SET is_deprecated = FALSE, updated_at = NOW()
        WHERE model_id IN ('claude-3-opus-20240229', 'claude-3-haiku-20240307')
        AND provider = 'anthropic';
    """)