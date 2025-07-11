#!/usr/bin/env python3
"""
Debug script to check why models aren't appearing in user settings.
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models.config import ModelConfiguration
from app.services.unified_config_service import UnifiedConfigService
from sqlalchemy import select

def debug_models():
    """Debug model availability issues."""
    
    with SessionLocal() as session:
        print("🔍 Debugging Model Availability...")
        
        # 1. Check direct database query
        print("\n1. Direct database query:")
        stmt = select(ModelConfiguration).filter(ModelConfiguration.is_available == True)
        available_models = session.execute(stmt).scalars().all()
        print(f"   Available models in DB: {len(available_models)}")
        
        # Show first few models
        for i, model in enumerate(available_models[:5]):
            print(f"   - {model.model_id} ({model.provider}) - Available: {model.is_available}")
        
        # 2. Check unified config service
        print("\n2. Unified config service:")
        try:
            config_service = UnifiedConfigService(session)
            service_models = config_service.get_available_models()
            print(f"   Models from service: {len(service_models)}")
            
            # Show first few models
            for i, model in enumerate(service_models[:5]):
                print(f"   - {model.model_id} ({model.provider})")
        except Exception as e:
            print(f"   Error with service: {e}")
        
        # 3. Check current configuration
        print("\n3. Current configuration:")
        try:
            current_config = config_service.get_current_config()
            print(f"   Current model: {current_config.model_id}")
            print(f"   Current provider: {current_config.provider}")
        except Exception as e:
            print(f"   Error getting current config: {e}")
        
        # 4. Check for any filtering issues
        print("\n4. Model filtering analysis:")
        all_models = session.execute(select(ModelConfiguration)).scalars().all()
        print(f"   Total models: {len(all_models)}")
        
        deprecated_models = [m for m in all_models if m.is_deprecated]
        print(f"   Deprecated models: {len(deprecated_models)}")
        
        unavailable_models = [m for m in all_models if not m.is_available]
        print(f"   Unavailable models: {len(unavailable_models)}")
        
        # 5. Show latest models specifically
        print("\n5. Latest models check:")
        latest_models = [
            'o4-mini', 'o3', 'o3-mini', 'o3-pro',
            'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-4.5',
            'claude-opus-4-20250514', 'claude-sonnet-4-20250514'
        ]
        
        for model_id in latest_models:
            model = session.execute(
                select(ModelConfiguration).filter_by(model_id=model_id)
            ).scalar_one_or_none()
            
            if model:
                status = "✅ Available" if model.is_available else "❌ Unavailable"
                deprecated = " (DEPRECATED)" if model.is_deprecated else ""
                print(f"   {model_id}: {status}{deprecated}")
            else:
                print(f"   {model_id}: ❌ Not found")

if __name__ == "__main__":
    debug_models()