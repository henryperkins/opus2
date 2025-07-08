#!/usr/bin/env python3
"""
Migration and seeding script for the new model configuration system.

This script:
1. Runs the migration to populate ModelConfiguration
2. Initializes the database with comprehensive model data
3. Validates the new configuration system
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.database import SessionLocal, async_engine
from app.services.unified_config_service import UnifiedConfigService
from app.services.model_service import ModelService
from app.models.config import ModelConfiguration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the model configuration migration."""
    import subprocess
    
    try:
        # Run the specific migration
        result = subprocess.run([
            "alembic", "upgrade", "013_populate_model_configurations"
        ], cwd=backend_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Migration completed successfully")
            if result.stdout:
                logger.info(f"Migration output: {result.stdout}")
        else:
            logger.error(f"Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run migration: {e}")
        return False
    
    return True


def validate_model_data():
    """Validate that models were populated correctly."""
    try:
        with SessionLocal() as db:
            # Check model count
            model_count = db.query(ModelConfiguration).count()
            logger.info(f"Found {model_count} models in database")
            
            if model_count == 0:
                logger.error("No models found in database")
                return False
            
            # Check specific models
            test_models = [
                "gpt-4o-mini",
                "gpt-4o", 
                "claude-sonnet-4-20250514",
                "o1-preview"
            ]
            
            for model_id in test_models:
                model = db.query(ModelConfiguration).filter_by(model_id=model_id).first()
                if model:
                    logger.info(f"✓ Found model: {model_id} ({model.name})")
                    
                    # Validate capabilities
                    if model.capabilities:
                        caps = model.capabilities
                        logger.info(f"  - Supports functions: {caps.get('supports_functions', 'N/A')}")
                        logger.info(f"  - Supports streaming: {caps.get('supports_streaming', 'N/A')}")
                        logger.info(f"  - Supports reasoning: {caps.get('supports_reasoning', 'N/A')}")
                    else:
                        logger.warning(f"  - No capabilities data for {model_id}")
                else:
                    logger.warning(f"✗ Model not found: {model_id}")
            
            return True
            
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False


def test_unified_config():
    """Test the unified configuration system."""
    try:
        with SessionLocal() as db:
            service = UnifiedConfigService(db)
            
            # Test getting current config
            config = service.get_current_config()
            logger.info(f"Current config: {config.provider}/{config.model_id}")
            
            # Test getting available models
            models = service.get_available_models()
            logger.info(f"Available models: {len(models)}")
            
            # Test model service
            model_service = ModelService(db)
            
            # Test capability queries
            test_model = "gpt-4o-mini"
            logger.info(f"Testing model service with {test_model}:")
            logger.info(f"  - Is reasoning model: {model_service.is_reasoning_model(test_model)}")
            logger.info(f"  - Supports streaming: {model_service.supports_streaming(test_model)}")
            logger.info(f"  - Supports functions: {model_service.supports_functions(test_model)}")
            logger.info(f"  - Max tokens: {model_service.get_max_tokens(test_model)}")
            
            return True
            
    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return False


def main():
    """Main migration and validation process."""
    logger.info("Starting model configuration migration and seeding...")
    
    # Step 1: Run migration
    logger.info("Step 1: Running database migration...")
    if not run_migration():
        logger.error("Migration failed, stopping")
        return 1
    
    # Step 2: Validate data
    logger.info("Step 2: Validating model data...")
    if not validate_model_data():
        logger.error("Data validation failed")
        return 1
    
    # Step 3: Test configuration system
    logger.info("Step 3: Testing configuration system...")
    if not test_unified_config():
        logger.error("Configuration system test failed")
        return 1
    
    logger.info("✅ Migration and seeding completed successfully!")
    logger.info("The model configuration system is now using the database as the single source of truth.")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)