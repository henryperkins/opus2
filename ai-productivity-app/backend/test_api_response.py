#!/usr/bin/env python3
"""
Test the actual API response structure to understand the frontend issue.
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.services.unified_config_service import UnifiedConfigService
from app.schemas.generation import ConfigResponse
import json

def test_api_response():
    """Test what the actual API response looks like."""
    
    with SessionLocal() as session:
        print("🔍 Testing API Response Structure...")
        
        # Get the service
        config_service = UnifiedConfigService(session)
        
        # Get current config and available models
        current_config = config_service.get_current_config()
        available_models = config_service.get_available_models()
        
        print(f"\n1. Current Config:")
        print(f"   Model: {current_config.model_id}")
        print(f"   Provider: {current_config.provider}")
        print(f"   Temperature: {current_config.temperature}")
        
        print(f"\n2. Available Models ({len(available_models)}):")
        for i, model in enumerate(available_models[:5]):
            print(f"   {i+1}. {model.model_id} ({model.provider})")
            print(f"      Display: {model.display_name}")
            print(f"      Capabilities: {list(model.capabilities.keys()) if model.capabilities else 'None'}")
        
        # Create the response structure that the API would return
        response_data = {
            "current": current_config.model_dump(),
            "available_models": [model.model_dump() for model in available_models],
            "providers": {
                "openai": {
                    "display_name": "OpenAI",
                    "models": [m.model_dump() for m in available_models if m.provider == "openai"],
                    "capabilities": {}
                },
                "anthropic": {
                    "display_name": "Anthropic",
                    "models": [m.model_dump() for m in available_models if m.provider == "anthropic"],
                    "capabilities": {}
                },
                "azure": {
                    "display_name": "Azure OpenAI",
                    "models": [m.model_dump() for m in available_models if m.provider == "azure"],
                    "capabilities": {}
                }
            }
        }
        
        print(f"\n3. Response Structure:")
        print(f"   Current config keys: {list(response_data['current'].keys())}")
        print(f"   Available models count: {len(response_data['available_models'])}")
        print(f"   Providers: {list(response_data['providers'].keys())}")
        
        # Check for key fields that frontend expects
        print(f"\n4. Frontend Compatibility Check:")
        if response_data['available_models']:
            first_model = response_data['available_models'][0]
            expected_fields = ['model_id', 'provider', 'display_name', 'capabilities']
            
            for field in expected_fields:
                if field in first_model:
                    print(f"   ✅ {field}: {first_model[field]}")
                else:
                    print(f"   ❌ {field}: MISSING")
        
        # Check current config fields
        print(f"\n5. Current Config Fields:")
        current_fields = ['model_id', 'provider', 'temperature', 'max_tokens']
        for field in current_fields:
            if field in response_data['current']:
                print(f"   ✅ {field}: {response_data['current'][field]}")
            else:
                print(f"   ❌ {field}: MISSING")
        
        # Save sample response for debugging
        with open('/tmp/sample_response.json', 'w') as f:
            json.dump(response_data, f, indent=2, default=str)
        print(f"\n✅ Sample response saved to /tmp/sample_response.json")

if __name__ == "__main__":
    test_api_response()