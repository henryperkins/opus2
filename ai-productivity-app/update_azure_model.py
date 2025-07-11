#!/usr/bin/env python3
"""
Utility script to update Azure OpenAI model configuration.
This script allows switching between available deployment names: gpt-4.1 and o3.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Set environment variables
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_PROVIDER"] = "azure"
os.environ["AZURE_OPENAI_API_KEY"] = os.getenv("AZURE_OPENAI_API_KEY", "your-azure-api-key-here")
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://oairesourcehp.openai.azure.com"
os.environ["AZURE_OPENAI_API_VERSION"] = "2025-04-01-preview"

AVAILABLE_MODELS = {
    "gpt-4.1": {
        "name": "GPT-4.1",
        "description": "Primary deployment for general use and code completion",
        "use_responses_api": False,
        "temperature": 0.2,
        "max_tokens": 200
    },
    "o3": {
        "name": "O3 Reasoning",
        "description": "Advanced reasoning model for complex code problems",
        "use_responses_api": True,
        "temperature": 0.1,
        "max_tokens": 150
    }
}

async def update_model_config(model_name: str):
    """Update the Azure OpenAI model configuration."""
    print(f"🔧 Updating Azure OpenAI configuration to use: {model_name}")
    
    if model_name not in AVAILABLE_MODELS:
        print(f"❌ Model '{model_name}' not available. Choose from: {list(AVAILABLE_MODELS.keys())}")
        return False
    
    try:
        from app.llm.client import llm_client
        from app.config import settings
        
        model_config = AVAILABLE_MODELS[model_name]
        
        # Update the settings
        settings.llm_default_model = model_name
        
        # Reconfigure the LLM client
        await llm_client.reconfigure(
            provider="azure",
            model=model_name,
            use_responses_api=model_config["use_responses_api"]
        )
        
        print(f"✅ Successfully configured Azure OpenAI:")
        print(f"   Model: {model_config['name']} ({model_name})")
        print(f"   Description: {model_config['description']}")
        print(f"   Uses Responses API: {model_config['use_responses_api']}")
        print(f"   Temperature: {model_config['temperature']}")
        print(f"   Max Tokens: {model_config['max_tokens']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update model configuration: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_model_completion(model_name: str):
    """Test code completion with the specified model."""
    print(f"\n🧪 Testing code completion with {model_name}...")
    
    try:
        from app.llm.client import llm_client
        
        # Simple code completion test
        messages = [
            {
                "role": "system", 
                "content": "You are an AI coding assistant specializing in JavaScript. Complete the code at the cursor position. Return only the code that should be inserted, without explanations or markdown."
            },
            {
                "role": "user",
                "content": "Complete this JavaScript function:\nfunction calculateSum(a, b) {\n    return"
            }
        ]
        
        model_config = AVAILABLE_MODELS[model_name]
        
        response = await llm_client.complete(
            messages=messages,
            max_tokens=model_config["max_tokens"],
            temperature=model_config["temperature"]
        )
        
        # Extract response
        if hasattr(response, 'choices') and response.choices:
            completion = response.choices[0].message.content or ""
        elif hasattr(response, 'output_text'):
            completion = response.output_text or ""
        elif hasattr(response, 'output'):
            completion = response.output or ""
        else:
            completion = str(response)
        
        print(f"✅ Code completion successful!")
        print(f"   Input: function calculateSum(a, b) {{ return")
        print(f"   Completion: '{completion.strip()}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Code completion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def list_available_models():
    """List all available Azure OpenAI models."""
    print("📋 Available Azure OpenAI Models:")
    print("=" * 40)
    
    for model_id, config in AVAILABLE_MODELS.items():
        print(f"🤖 {config['name']} ({model_id})")
        print(f"   Description: {config['description']}")
        print(f"   Uses Responses API: {config['use_responses_api']}")
        print(f"   Optimal Temperature: {config['temperature']}")
        print(f"   Max Tokens: {config['max_tokens']}")
        print()

async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("🚀 Azure OpenAI Model Configuration Tool")
        print("=" * 40)
        await list_available_models()
        print("Usage:")
        print(f"  python {sys.argv[0]} <model_name>")
        print(f"  python {sys.argv[0]} gpt-4.1")
        print(f"  python {sys.argv[0]} o3")
        return 1
    
    model_name = sys.argv[1]
    
    print("🚀 Azure OpenAI Model Configuration")
    print("=" * 40)
    
    # Update model configuration
    if not await update_model_config(model_name):
        return 1
    
    # Test the model
    if not await test_model_completion(model_name):
        return 1
    
    print("\n🎉 Model configuration and testing completed successfully!")
    print(f"The Azure OpenAI client is now configured to use: {AVAILABLE_MODELS[model_name]['name']}")
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)