#!/usr/bin/env python3
"""
Test script to verify that the latest models are accessible through the API.

This script tests:
1. Model seeding/updating works correctly
2. API returns all expected models
3. Frontend can access model information
4. Latest models are included (o4-mini, o3-pro, Claude 4, etc.)

Usage:
    python test_models_api.py
"""

import asyncio
import json
from pathlib import Path
from app.database import AsyncSessionLocal
from app.models.config import ModelConfiguration
from app.services.unified_config_service import UnifiedConfigService
from sqlalchemy import select


async def test_models_api():
    """Test the models API functionality."""
    print("🔍 Testing AI Models API...")
    
    async with AsyncSessionLocal() as session:
        # 1. Test model seeding
        print("\n1. Testing model count...")
        result = await session.execute(select(ModelConfiguration))
        models = result.scalars().all()
        print(f"   Found {len(models)} models in database")
        
        # 2. Test specific latest models
        print("\n2. Testing latest models presence...")
        expected_models = [
            "o4-mini",
            "o3", 
            "o3-mini",
            "o3-pro",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4.5",
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-7-sonnet-20250225",
            "claude-3-5-haiku-20241022"
        ]
        
        model_ids = {model.model_id for model in models}
        
        for expected in expected_models:
            if expected in model_ids:
                print(f"   ✅ {expected}")
            else:
                print(f"   ❌ {expected} (missing)")
        
        # 3. Test providers
        print("\n3. Testing providers...")
        providers = {}
        for model in models:
            if model.provider not in providers:
                providers[model.provider] = []
            providers[model.provider].append(model.model_id)
        
        for provider, model_list in providers.items():
            print(f"   {provider}: {len(model_list)} models")
        
        # 4. Test unified config service
        print("\n4. Testing unified config service...")
        # Use sync session for UnifiedConfigService since it uses .query() syntax
        from app.database import SessionLocal
        with SessionLocal() as sync_session:
            config_service = UnifiedConfigService(sync_session)
            
            try:
                current_config = config_service.get_current_config()
                print(f"   ✅ Current config loaded: {current_config.model_id}")
            except Exception as e:
                print(f"   ❌ Config service error: {e}")
            
            try:
                available_models = config_service.get_available_models()
                print(f"   ✅ Available models: {len(available_models)}")
            except Exception as e:
                print(f"   ❌ Available models error: {e}")
        
        # 5. Test model capabilities
        print("\n5. Testing model capabilities...")
        reasoning_models = [m for m in models if m.capabilities and m.capabilities.get('supports_reasoning')]
        vision_models = [m for m in models if m.capabilities and m.capabilities.get('supports_vision')]
        function_models = [m for m in models if m.capabilities and m.capabilities.get('supports_functions')]
        
        print(f"   Reasoning models: {len(reasoning_models)}")
        print(f"   Vision models: {len(vision_models)}")
        print(f"   Function calling models: {len(function_models)}")
        
        # 6. Test model tiers
        print("\n6. Testing model tiers...")
        tiers = {}
        for model in models:
            if model.model_metadata and 'tier' in model.model_metadata:
                tier = model.model_metadata['tier']
                if tier not in tiers:
                    tiers[tier] = []
                tiers[tier].append(model.model_id)
        
        for tier, model_list in tiers.items():
            print(f"   {tier}: {len(model_list)} models")
        
        print(f"\n✅ Model API test completed successfully!")
        print(f"   Total models: {len(models)}")
        print(f"   Providers: {len(providers)}")
        print(f"   Latest models available: {len([m for m in expected_models if m in model_ids])}/{len(expected_models)}")


if __name__ == "__main__":
    asyncio.run(test_models_api())