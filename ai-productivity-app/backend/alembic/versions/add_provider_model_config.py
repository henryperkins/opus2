"""Add provider-specific model configuration support

Revision ID: add_provider_model_config
Revises: 
Create Date: 2025-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_provider_model_config'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add index on model_id + provider combination for faster lookups
    op.create_index(
        'ix_model_configurations_model_provider',
        'model_configurations',
        ['model_id', 'provider'],
        unique=False
    )
    
    # Insert default model configurations if they don't exist
    # This ensures all providers have proper model entries
    op.execute("""
        INSERT INTO model_configurations (model_id, name, provider, model_family, is_available, capabilities, default_params)
        VALUES 
        -- OpenAI models
        ('gpt-4o', 'GPT-4 Omni', 'openai', 'gpt-4', true, 
         '{"supports_functions": true, "supports_streaming": true, "supports_vision": true, "supports_json_mode": true, "max_context_window": 128000, "max_output_tokens": 4096}',
         '{"temperature": 0.7, "top_p": 1.0}'),
        ('gpt-4o-mini', 'GPT-4 Omni Mini', 'openai', 'gpt-4', true,
         '{"supports_functions": true, "supports_streaming": true, "supports_vision": true, "supports_json_mode": true, "max_context_window": 128000, "max_output_tokens": 4096}',
         '{"temperature": 0.7, "top_p": 1.0}'),
        
        -- Azure models
        ('gpt-4.1', 'GPT-4.1 (Azure)', 'azure', 'gpt-4', true,
         '{"supports_functions": true, "supports_streaming": true, "supports_vision": true, "supports_responses_api": true, "max_context_window": 128000, "max_output_tokens": 4096}',
         '{"temperature": 0.7, "top_p": 1.0}'),
        ('gpt-4.1-mini', 'GPT-4.1 Mini (Azure)', 'azure', 'gpt-4', true,
         '{"supports_functions": true, "supports_streaming": true, "supports_vision": true, "supports_responses_api": true, "max_context_window": 128000, "max_output_tokens": 4096}',
         '{"temperature": 0.7, "top_p": 1.0}'),
        ('o3', 'O3 Reasoning (Azure)', 'azure', 'reasoning', true,
         '{"supports_functions": false, "supports_streaming": false, "supports_reasoning": true, "supports_responses_api": true, "max_context_window": 200000, "max_output_tokens": 65536}',
         '{}'),
        ('o3-mini', 'O3 Mini Reasoning (Azure)', 'azure', 'reasoning', true,
         '{"supports_functions": false, "supports_streaming": false, "supports_reasoning": true, "supports_responses_api": true, "max_context_window": 200000, "max_output_tokens": 65536}',
         '{}'),
        
        -- Anthropic models
        ('claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet', 'anthropic', 'claude', true,
         '{"supports_functions": true, "supports_streaming": true, "supports_thinking": true, "max_context_window": 200000, "max_output_tokens": 4096}',
         '{"temperature": 0.7, "top_p": 1.0}'),
        ('claude-opus-4-20250514', 'Claude Opus 4', 'anthropic', 'claude', true,
         '{"supports_functions": true, "supports_streaming": true, "supports_thinking": true, "max_context_window": 200000, "max_output_tokens": 4096}',
         '{"temperature": 0.7, "top_p": 1.0}'),
        ('claude-sonnet-4-20250514', 'Claude Sonnet 4', 'anthropic', 'claude', true,
         '{"supports_functions": true, "supports_streaming": true, "supports_thinking": true, "max_context_window": 200000, "max_output_tokens": 4096}',
         '{"temperature": 0.7, "top_p": 1.0}')
        ON CONFLICT (model_id) DO UPDATE SET
            capabilities = EXCLUDED.capabilities,
            default_params = EXCLUDED.default_params,
            is_available = EXCLUDED.is_available;
    """)
    
    # Update cost information for models
    op.execute("""
        UPDATE model_configurations SET
            cost_input_per_1k = CASE
                WHEN model_id = 'gpt-4o' THEN 0.005
                WHEN model_id = 'gpt-4o-mini' THEN 0.00015
                WHEN model_id = 'gpt-4.1' THEN 0.005
                WHEN model_id = 'gpt-4.1-mini' THEN 0.00015
                WHEN model_id = 'o3' THEN 0.015
                WHEN model_id = 'o3-mini' THEN 0.001
                WHEN model_id = 'claude-3-5-sonnet-20241022' THEN 0.003
                WHEN model_id = 'claude-opus-4-20250514' THEN 0.015
                WHEN model_id = 'claude-sonnet-4-20250514' THEN 0.003
                ELSE 0.001
            END,
            cost_output_per_1k = CASE
                WHEN model_id = 'gpt-4o' THEN 0.015
                WHEN model_id = 'gpt-4o-mini' THEN 0.0006
                WHEN model_id = 'gpt-4.1' THEN 0.015
                WHEN model_id = 'gpt-4.1-mini' THEN 0.0006
                WHEN model_id = 'o3' THEN 0.06
                WHEN model_id = 'o3-mini' THEN 0.004
                WHEN model_id = 'claude-3-5-sonnet-20241022' THEN 0.015
                WHEN model_id = 'claude-opus-4-20250514' THEN 0.075
                WHEN model_id = 'claude-sonnet-4-20250514' THEN 0.015
                ELSE 0.002
            END
        WHERE model_id IN (
            'gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini',
            'o3', 'o3-mini', 'claude-3-5-sonnet-20241022',
            'claude-opus-4-20250514', 'claude-sonnet-4-20250514'
        );
    """)


def downgrade():
    op.drop_index('ix_model_configurations_model_provider', table_name='model_configurations')
