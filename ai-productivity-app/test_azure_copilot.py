#!/usr/bin/env python3
"""
Quick test script to verify Azure OpenAI configuration for Monacopilot integration.
This script tests the /api/code/copilot endpoint to ensure it's working with Azure OpenAI.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add backend to path so we can import modules
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Set environment variables for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_PROVIDER"] = "azure"
os.environ["AZURE_OPENAI_API_KEY"] = os.getenv("AZURE_OPENAI_API_KEY", "your-azure-api-key-here")
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://oairesourcehp.openai.azure.com"
os.environ["AZURE_OPENAI_API_VERSION"] = "2025-04-01-preview"
os.environ["LLM_DEFAULT_MODEL"] = "gpt-4.1"

async def test_azure_openai_basic():
    """Test basic Azure OpenAI client functionality."""
    print("🔧 Testing Azure OpenAI client initialization...")
    
    try:
        from app.llm.client import llm_client
        
        # Ensure client is configured for Azure
        await llm_client.reconfigure(
            provider="azure",
            model="gpt-4.1",  # Using the actual deployment name
            use_responses_api=True
        )
        
        print(f"✅ LLM Client initialized successfully")
        print(f"   Provider: {llm_client.provider}")
        print(f"   Model: {llm_client.active_model}")
        print(f"   Uses Responses API: {llm_client.use_responses_api}")
        
        return True
        
    except Exception as e:
        print(f"❌ Azure OpenAI client failed: {e}")
        return False

async def test_copilot_completion():
    """Test code completion via the copilot endpoint logic."""
    print("\n🔧 Testing Monacopilot completion logic...")
    
    try:
        from app.routers.copilot import build_completion_prompt, clean_completion
        from app.llm.client import llm_client
        
        # Create mock completion metadata
        mock_metadata = type('MockMetadata', (), {
            'language': 'javascript',
            'textBeforeCursor': 'function calculateSum(a, b) {\n    return',
            'textAfterCursor': '\n}',
            'filename': 'calculator.js',
            'technologies': ['javascript', 'react'],
            'cursorPosition': {'lineNumber': 2, 'column': 11},
            'editorState': {'completionMode': 'continue'}
        })()
        
        # Build completion prompt
        prompt = build_completion_prompt(mock_metadata)
        print(f"📝 Generated prompt preview:\n{prompt[:200]}...")
        
        # Build messages for LLM client
        messages = [
            {"role": "system", "content": prompt.split("\n\nUser:")[0].replace("System: ", "")},
            {"role": "user", "content": prompt.split("\n\nUser:")[1].split("\n\nAssistant:")[0] if "\n\nUser:" in prompt else prompt}
        ]
        
        # Test with Azure OpenAI
        response = await llm_client.complete(
            messages=messages,
            max_tokens=200,
            temperature=0.2
        )
        
        # Extract completion text
        if hasattr(response, 'choices') and response.choices:
            completion_text = response.choices[0].message.content or ""
        elif hasattr(response, 'output_text'):
            completion_text = response.output_text or ""
        elif hasattr(response, 'output'):
            completion_text = response.output or ""
        else:
            completion_text = str(response).strip()
        
        # Clean completion
        cleaned_completion = clean_completion(completion_text)
        
        print(f"✅ Code completion successful!")
        print(f"   Raw response length: {len(completion_text)} chars")
        print(f"   Cleaned completion: '{cleaned_completion.strip()}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Copilot completion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_configuration_system():
    """Test the configuration system for Azure OpenAI."""
    print("\n🔧 Testing configuration system...")
    
    try:
        from app.config import settings
        
        print(f"✅ Configuration loaded successfully")
        print(f"   LLM Provider: {settings.llm_provider}")
        print(f"   Azure Endpoint: {settings.azure_openai_endpoint}")
        print(f"   Azure API Version: {settings.azure_openai_api_version}")
        print(f"   Default Model: {settings.llm_default_model}")
        print(f"   Azure API Key: {'*' * 20}...{settings.azure_openai_api_key[-4:] if settings.azure_openai_api_key else 'NOT SET'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Testing Azure OpenAI + Monacopilot Integration")
    print("=" * 50)
    
    results = []
    
    # Test configuration
    results.append(await test_configuration_system())
    
    # Test basic Azure OpenAI
    results.append(await test_azure_openai_basic())
    
    # Test copilot completion
    results.append(await test_copilot_completion())
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed! Azure OpenAI + Monacopilot integration is working!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)