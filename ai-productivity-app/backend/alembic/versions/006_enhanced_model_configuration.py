"""Enhanced model configuration storage for PostgreSQL

Revision ID: 006_enhanced_model_configuration
Revises: 005_postgresql_optimizations
Create Date: 2024-06-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = '006_enhanced_model_configuration'
down_revision = '005_postgresql_optimizations'
branch_labels = None
depends_on = None


def upgrade():
    """Add enhanced model configuration storage with PostgreSQL features"""
    
    # Get database engine to check if we're using PostgreSQL
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    if is_postgresql:
        # Create PostgreSQL enum types
        op.execute("""
            CREATE TYPE model_provider_enum AS ENUM (
                'openai', 'azure', 'anthropic', 'local', 'ollama'
            )
        """)
        
        op.execute("""
            CREATE TYPE model_capability_enum AS ENUM (
                'chat', 'completion', 'embedding', 'vision', 'function_calling', 
                'code_generation', 'reasoning', 'multimodal'
            )
        """)
        
        # Upgrade existing RuntimeConfig table to use JSONB
        op.execute("ALTER TABLE runtime_config ALTER COLUMN value TYPE JSONB USING value::jsonb")
        
        # Upgrade ConfigHistory table to use JSONB
        op.execute("ALTER TABLE config_history ALTER COLUMN old_value TYPE JSONB USING old_value::jsonb")
        op.execute("ALTER TABLE config_history ALTER COLUMN new_value TYPE JSONB USING new_value::jsonb")
    
    # Create model_configurations table
    op.create_table(
        'model_configurations',
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('provider', 
                 postgresql.ENUM('openai', 'azure', 'anthropic', 'local', 'ollama', 
                               name='model_provider_enum', create_type=False) if is_postgresql 
                 else sa.String(20), nullable=False),
        sa.Column('model_family', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=100), nullable=True),
        sa.Column('capabilities', 
                 postgresql.JSONB() if is_postgresql else sa.JSON(), 
                 nullable=False, server_default='[]'),
        sa.Column('default_params', 
                 postgresql.JSONB() if is_postgresql else sa.JSON(), 
                 nullable=False, server_default='{}'),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='4096'),
        sa.Column('context_window', sa.Integer(), nullable=False, server_default='8192'),
        sa.Column('cost_input_per_1k', sa.Float(), nullable=True),
        sa.Column('cost_output_per_1k', sa.Float(), nullable=True),
        sa.Column('avg_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('throughput_tokens_per_sec', sa.Float(), nullable=True),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_deprecated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata', 
                 postgresql.JSONB() if is_postgresql else sa.JSON(), 
                 nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('deprecated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('model_id'),
        sa.CheckConstraint('max_tokens > 0', name='positive_max_tokens'),
        sa.CheckConstraint('context_window > 0', name='positive_context_window'),
        sa.CheckConstraint('cost_input_per_1k >= 0', name='non_negative_input_cost'),
        sa.CheckConstraint('cost_output_per_1k >= 0', name='non_negative_output_cost'),
        sa.CheckConstraint('avg_response_time_ms > 0', name='positive_response_time'),
        sa.CheckConstraint('throughput_tokens_per_sec > 0', name='positive_throughput'),
        comment='Enhanced model configuration storage with PostgreSQL optimization'
    )
    
    # Create model_usage_metrics table
    op.create_table(
        'model_usage_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens_input', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens_output', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_response_time_ms', sa.Float(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('avg_user_rating', sa.Float(), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('detailed_metrics', 
                 postgresql.JSONB() if is_postgresql else sa.JSON(), 
                 nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('total_requests >= 0', name='non_negative_requests'),
        sa.CheckConstraint('total_tokens_input >= 0', name='non_negative_input_tokens'),
        sa.CheckConstraint('total_tokens_output >= 0', name='non_negative_output_tokens'),
        sa.CheckConstraint('success_rate >= 0 AND success_rate <= 100', name='valid_success_rate'),
        sa.CheckConstraint('avg_user_rating >= 1 AND avg_user_rating <= 5', name='valid_user_rating'),
        sa.CheckConstraint('period_start < period_end', name='valid_time_period'),
        sa.CheckConstraint('total_cost >= 0', name='non_negative_cost'),
        comment='Track model usage and performance metrics'
    )
    
    # Create indexes
    op.create_index('idx_model_config_model_id', 'model_configurations', ['model_id'])
    op.create_index('idx_model_config_model_family', 'model_configurations', ['model_family'])
    op.create_index('idx_model_usage_model_id', 'model_usage_metrics', ['model_id'])
    
    if is_postgresql:
        # PostgreSQL-specific indexes
        
        # Model configurations indexes
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_config_capabilities_gin 
            ON model_configurations USING gin(capabilities)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_config_params_gin 
            ON model_configurations USING gin(default_params)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_config_metadata_gin 
            ON model_configurations USING gin(metadata)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_config_provider_family 
            ON model_configurations (provider, model_family)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_config_available 
            ON model_configurations (provider, model_family, is_available) 
            WHERE is_available = true AND is_deprecated = false
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_config_cost_efficiency 
            ON model_configurations (cost_input_per_1k, cost_output_per_1k, throughput_tokens_per_sec)
        """)
        
        # Model usage metrics indexes
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_usage_model_period 
            ON model_usage_metrics (model_id, period_start, period_end)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_usage_metrics_gin 
            ON model_usage_metrics USING gin(detailed_metrics)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_usage_recent 
            ON model_usage_metrics (model_id, period_end)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_usage_efficiency 
            ON model_usage_metrics (total_cost, total_requests)
        """)
        
        # Enhanced RuntimeConfig indexes
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_runtime_config_value_gin 
            ON runtime_config USING gin(value)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_runtime_config_model_configs 
            ON runtime_config (key, value) 
            WHERE key LIKE '%model%' OR key LIKE '%provider%'
        """)
        
        # Enhanced ConfigHistory indexes
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_history_key_time 
            ON config_history (config_key, changed_at)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_history_old_value_gin 
            ON config_history USING gin(old_value)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_history_new_value_gin 
            ON config_history USING gin(new_value)
        """)
        
        op.execute("""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_history_key_date 
            ON config_history (config_key, changed_at)
        """)
        
        # Add check constraints to existing tables
        try:
            op.execute("""
                ALTER TABLE runtime_config 
                ADD CONSTRAINT valid_value_type 
                CHECK (value_type IN ('string', 'number', 'boolean', 'object', 'array'))
            """)
            
            op.execute("""
                ALTER TABLE runtime_config 
                ADD CONSTRAINT valid_config_key_format 
                CHECK (key ~ '^[a-z][a-z0-9_]*$')
            """)
        except Exception:
            # Constraints may already exist or data may not conform
            pass


def downgrade():
    """Remove enhanced model configuration storage"""
    
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == 'postgresql'
    
    # Drop tables
    op.drop_table('model_usage_metrics')
    op.drop_table('model_configurations')
    
    if is_postgresql:
        # Drop PostgreSQL enum types
        op.execute("DROP TYPE IF EXISTS model_provider_enum")
        op.execute("DROP TYPE IF EXISTS model_capability_enum")
        
        # Revert RuntimeConfig back to JSON (if needed)
        op.execute("ALTER TABLE runtime_config ALTER COLUMN value TYPE JSON USING value::json")
        op.execute("ALTER TABLE config_history ALTER COLUMN old_value TYPE JSON USING old_value::json")
        op.execute("ALTER TABLE config_history ALTER COLUMN new_value TYPE JSON USING new_value::json")
        
        # Drop the new indexes
        indexes_to_drop = [
            'idx_runtime_config_value_gin',
            'idx_runtime_config_model_configs',
            'idx_config_history_key_time',
            'idx_config_history_old_value_gin',
            'idx_config_history_new_value_gin',
            'idx_config_history_key_date'
        ]
        
        for index_name in indexes_to_drop:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {index_name}")
        
        # Drop check constraints
        try:
            op.execute("ALTER TABLE runtime_config DROP CONSTRAINT IF EXISTS valid_value_type")
            op.execute("ALTER TABLE runtime_config DROP CONSTRAINT IF EXISTS valid_config_key_format")
        except Exception:
            pass