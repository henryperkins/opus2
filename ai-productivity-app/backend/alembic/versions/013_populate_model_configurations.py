"""Populate model configurations with comprehensive data

Revision ID: 013_populate_model_configurations
Revises: 012_fix_runtime_config_keys
Create Date: 2025-07-08 12:00:00.000000

"""
import json
import os
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '013_populate_model_configurations'
down_revision = '012_fix_runtime_config_keys'
branch_labels = None
depends_on = None


def upgrade():
    """Populate ModelConfiguration table with comprehensive model data."""
    
    # Get the fixtures file path
    fixtures_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'app', 'cli', 'fixtures', 'models_complete.json'
    )
    
    # If the comprehensive fixtures don't exist, try the basic one
    if not os.path.exists(fixtures_path):
        fixtures_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'app', 'cli', 'fixtures', 'models.json'
        )
    
    if not os.path.exists(fixtures_path):
        print(f"Warning: Model fixtures not found at {fixtures_path}")
        return
    
    # Load fixtures
    with open(fixtures_path, 'r') as f:
        models_data = json.load(f)
    
    # Get database connection
    bind = op.get_bind()
    session = Session(bind=bind)
    
    try:
        # Clear existing models to avoid conflicts (optional - remove if you want to preserve existing)
        # session.execute(text("DELETE FROM model_configurations"))
        
        # Insert or update each model
        for model_data in models_data:
            # Check if model already exists
            result = session.execute(
                text("SELECT model_id FROM model_configurations WHERE model_id = :model_id"),
                {"model_id": model_data["model_id"]}
            ).first()
            
            if result:
                # Update existing model
                session.execute(
                    text("""
                        UPDATE model_configurations 
                        SET name = :name,
                            provider = :provider,
                            model_family = :model_family,
                            version = :version,
                            capabilities = :capabilities,
                            default_params = :default_params,
                            max_tokens = :max_tokens,
                            context_window = :context_window,
                            cost_input_per_1k = :cost_input_per_1k,
                            cost_output_per_1k = :cost_output_per_1k,
                            avg_response_time_ms = :avg_response_time_ms,
                            throughput_tokens_per_sec = :throughput_tokens_per_sec,
                            is_available = :is_available,
                            is_deprecated = :is_deprecated,
                            model_metadata = :model_metadata,
                            updated_at = :updated_at,
                            deprecated_at = :deprecated_at
                        WHERE model_id = :model_id
                    """),
                    {
                        "model_id": model_data["model_id"],
                        "name": model_data["name"],
                        "provider": model_data["provider"],
                        "model_family": model_data["model_family"],
                        "version": model_data.get("version"),
                        "capabilities": json.dumps(model_data.get("capabilities", {})),
                        "default_params": json.dumps(model_data.get("default_params", {})),
                        "max_tokens": model_data.get("max_tokens", 4096),
                        "context_window": model_data.get("context_window", 8192),
                        "cost_input_per_1k": model_data.get("cost_input_per_1k"),
                        "cost_output_per_1k": model_data.get("cost_output_per_1k"),
                        "avg_response_time_ms": model_data.get("avg_response_time_ms"),
                        "throughput_tokens_per_sec": model_data.get("throughput_tokens_per_sec"),
                        "is_available": model_data.get("is_available", True),
                        "is_deprecated": model_data.get("is_deprecated", False),
                        "model_metadata": json.dumps(model_data.get("model_metadata", {})),
                        "updated_at": datetime.utcnow(),
                        "deprecated_at": model_data.get("deprecated_at")
                    }
                )
            else:
                # Insert new model
                session.execute(
                    text("""
                        INSERT INTO model_configurations (
                            model_id, name, provider, model_family, version,
                            capabilities, default_params, max_tokens, context_window,
                            cost_input_per_1k, cost_output_per_1k,
                            avg_response_time_ms, throughput_tokens_per_sec,
                            is_available, is_deprecated, model_metadata,
                            created_at, updated_at, deprecated_at
                        ) VALUES (
                            :model_id, :name, :provider, :model_family, :version,
                            :capabilities, :default_params, :max_tokens, :context_window,
                            :cost_input_per_1k, :cost_output_per_1k,
                            :avg_response_time_ms, :throughput_tokens_per_sec,
                            :is_available, :is_deprecated, :model_metadata,
                            :created_at, :updated_at, :deprecated_at
                        )
                    """),
                    {
                        "model_id": model_data["model_id"],
                        "name": model_data["name"],
                        "provider": model_data["provider"],
                        "model_family": model_data["model_family"],
                        "version": model_data.get("version"),
                        "capabilities": json.dumps(model_data.get("capabilities", {})),
                        "default_params": json.dumps(model_data.get("default_params", {})),
                        "max_tokens": model_data.get("max_tokens", 4096),
                        "context_window": model_data.get("context_window", 8192),
                        "cost_input_per_1k": model_data.get("cost_input_per_1k"),
                        "cost_output_per_1k": model_data.get("cost_output_per_1k"),
                        "avg_response_time_ms": model_data.get("avg_response_time_ms"),
                        "throughput_tokens_per_sec": model_data.get("throughput_tokens_per_sec"),
                        "is_available": model_data.get("is_available", True),
                        "is_deprecated": model_data.get("is_deprecated", False),
                        "model_metadata": json.dumps(model_data.get("model_metadata", {})),
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "deprecated_at": model_data.get("deprecated_at")
                    }
                )
        
        session.commit()
        print(f"Successfully populated {len(models_data)} models in ModelConfiguration table")
        
    except Exception as e:
        session.rollback()
        print(f"Error populating models: {e}")
        raise
    finally:
        session.close()


def downgrade():
    """Remove populated model configurations."""
    # This is optional - you might want to keep the data
    # If you want to remove all models on downgrade:
    # op.execute("DELETE FROM model_configurations")
    pass