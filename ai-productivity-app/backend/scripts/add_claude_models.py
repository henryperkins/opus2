#!/usr/bin/env python3
"""
Script to add Claude Sonnet and Opus 4 models to the database.
"""

import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session
from app.database import get_db, engine
from app.models.config import ModelConfiguration
from app.services.config_service import ConfigService

def add_claude_models():
    """Add Claude Sonnet and Opus 4 models to the database."""
    
    claude_models = [
        {
            "model_id": "claude-opus-4-20250514",
            "name": "Claude Opus 4",
            "provider": "anthropic",
            "model_family": "claude-4",
            "version": "20250514",
            "capabilities": ["chat", "multimodal", "function_calling", "reasoning", "vision"],
            "default_params": {
                "temperature": 0.7,
                "max_tokens": 4000,
                "top_p": 1.0
            },
            "max_tokens": 4000,
            "context_window": 200000,
            "cost_input_per_1k": 0.015,
            "cost_output_per_1k": 0.075,
            "avg_response_time_ms": 3000,
            "throughput_tokens_per_sec": 50.0,
            "is_available": True,
            "is_deprecated": False,
            "model_metadata": {
                "description": "Our most capable and intelligent model",
                "training_cutoff": "March 2025",
                "supports_vision": True,
                "supports_reasoning": True,
                "performance_tier": "powerful"
            }
        },
        {
            "model_id": "claude-sonnet-4-20250514",
            "name": "Claude Sonnet 4",
            "provider": "anthropic",
            "model_family": "claude-4",
            "version": "20250514",
            "capabilities": ["chat", "multimodal", "function_calling", "reasoning", "vision"],
            "default_params": {
                "temperature": 0.7,
                "max_tokens": 4000,
                "top_p": 1.0
            },
            "max_tokens": 4000,
            "context_window": 200000,
            "cost_input_per_1k": 0.003,
            "cost_output_per_1k": 0.015,
            "avg_response_time_ms": 2000,
            "throughput_tokens_per_sec": 75.0,
            "is_available": True,
            "is_deprecated": False,
            "model_metadata": {
                "description": "High-performance model with exceptional reasoning",
                "training_cutoff": "March 2025",
                "supports_vision": True,
                "supports_reasoning": True,
                "performance_tier": "balanced"
            }
        }
    ]
    
    # Create a database session
    db = next(get_db())
    config_service = ConfigService(db)
    
    try:
        for model_data in claude_models:
            # Check if model already exists
            existing = db.query(ModelConfiguration).filter_by(model_id=model_data["model_id"]).first()
            
            if existing:
                print(f"Model {model_data['model_id']} already exists. Updating...")
                # Update existing model
                for key, value in model_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
            else:
                print(f"Adding new model: {model_data['model_id']}")
                # Create new model configuration
                config_service.create_model_configuration(model_data)
        
        db.commit()
        print("Successfully added/updated Claude models!")
        
        # List all models to verify
        print("\nCurrent models in database:")
        models = db.query(ModelConfiguration).all()
        for model in models:
            print(f"  - {model.model_id} ({model.provider})")
    
    except Exception as e:
        db.rollback()
        print(f"Error adding models: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Adding Claude Sonnet and Opus 4 models to database...")
    add_claude_models()