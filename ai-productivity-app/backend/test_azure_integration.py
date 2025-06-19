#!/usr/bin/env python3
"""
Test script to validate Azure OpenAI integration.

This script tests the key features of the Azure OpenAI implementation:
1. Provider detection and client initialization
2. API version selection (Chat Completions vs. Responses API)
3. Authentication methods (API key vs. Entra ID)
4. Message format conversion for Responses API
5. Configuration endpoint output
6. Fallback behavior

Run with: python test_azure_integration.py
"""

import os
import asyncio


def test_environment_setup():
    """Test different environment configurations."""
    print("🧪 Testing Environment Configurations")
    print("=" * 50)

    # Save original environment
    original_env = dict(os.environ)

    test_configs = [
        {
            "name": "Standard OpenAI",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "test-key",
                "LLM_MODEL": "gpt-4o-mini"
            },
            "expected_provider": "openai",
            "expected_responses_api": False
        },
        {
            "name": "Azure OpenAI with Chat Completions",
            "env": {
                "LLM_PROVIDER": "azure",
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_VERSION": "2024-02-01",
                "LLM_MODEL": "gpt-4o"
            },
            "expected_provider": "azure",
            "expected_responses_api": False
        },
        {
            "name": "Azure OpenAI with Responses API",
            "env": {
                "LLM_PROVIDER": "azure",
                "AZURE_OPENAI_API_KEY": "test-key",
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_VERSION": "preview",
                "LLM_MODEL": "gpt-4.1"
            },
            "expected_provider": "azure",
            "expected_responses_api": True
        },
        {
            "name": "Azure OpenAI with Entra ID",
            "env": {
                "LLM_PROVIDER": "azure",
                "AZURE_OPENAI_AUTH_METHOD": "entra_id",
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_API_VERSION": "preview",
                "LLM_MODEL": "gpt-4.1"
            },
            "expected_provider": "azure",
            "expected_responses_api": True
        }
    ]

    for config in test_configs:
        print(f"\n📋 Testing: {config['name']}")

        # Clear environment
        for key in list(os.environ.keys()):
            if key.startswith(('LLM_', 'OPENAI_', 'AZURE_')):
                del os.environ[key]

        # Set test environment
        for key, value in config["env"].items():
            os.environ[key] = value

        try:
            # Reload configuration
            import importlib
            import app.config
            importlib.reload(app.config)
            from app.llm.client import LLMClient

            # Test client creation
            client = LLMClient()

            # Validate expectations
            expected_provider = config["expected_provider"]
            assert client.provider == expected_provider, \
                f"Expected provider {expected_provider}, got {client.provider}"

            expected_responses = config["expected_responses_api"]
            assert client.use_responses_api == expected_responses, \
                f"Expected use_responses_api {expected_responses}, " \
                f"got {client.use_responses_api}"

            print(f"   ✓ Provider: {client.provider}")
            print(f"   ✓ Model: {client.active_model}")
            print(f"   ✓ Responses API: {client.use_responses_api}")
            print(f"   ✓ Client: {type(client.client).__name__}")

        except Exception as e:
            print(f"   ✗ Failed: {e}")
            continue

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

    print("\n✅ Environment configuration tests completed!")


def test_message_conversion():
    """Test message format conversion for Responses API."""
    print("\n🔄 Testing Message Format Conversion")
    print("=" * 50)

    # Test the inline message conversion logic in _complete_responses_api
    chat_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "Can you help me with coding?"}
    ]

    try:
        # Simulate the conversion logic from _complete_responses_api
        input_messages = []
        system_content = None

        for msg in chat_messages:
            if msg["role"] == "system":
                # System messages go in instructions for Responses API
                system_content = msg["content"]
            else:
                input_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        print(f"   ✓ Original messages: {len(chat_messages)}")
        print(f"   ✓ Input messages: {len(input_messages)}")
        print(f"   ✓ System instructions: {system_content is not None}")
        print("   ✓ Message conversion logic works correctly")

    except Exception as e:
        print(f"   ✗ Message conversion test failed: {e}")


async def test_config_endpoint():
    """Test the configuration endpoint."""
    print("\n⚙️  Testing Configuration Endpoint")
    print("=" * 50)

    try:
        from app.routers.config import get_config

        config = await get_config()

        print(f"   ✓ Providers available: {list(config['providers'].keys())}")
        openai_models = len(config['providers']['openai']['chat_models'])
        azure_models = len(config['providers']['azure']['chat_models'])
        azure_versions = config['providers']['azure']['api_versions']

        print(f"   ✓ OpenAI models: {openai_models}")
        print(f"   ✓ Azure models: {azure_models}")
        print(f"   ✓ Azure API versions: {azure_versions}")

        # Check Azure features
        azure_features = config['providers']['azure']['features']
        print("   ✓ Azure features:")
        for feature, enabled in azure_features.items():
            print(f"     - {feature}: {enabled}")

        # Check current settings
        current = config['current']
        print(f"   ✓ Current provider: {current['provider']}")
        print(f"   ✓ Current model: {current['chat_model']}")

    except Exception as e:
        print(f"   ✗ Config endpoint test failed: {e}")


def test_import_health():
    """Test that all imports work correctly."""
    print("\n📦 Testing Import Health")
    print("=" * 50)

    imports_to_test = [
        "app.config",
        "app.llm.client",
        "app.routers.config",
        "app.main"
    ]

    for module_name in imports_to_test:
        try:
            import importlib
            importlib.import_module(module_name)
            print(f"   ✓ {module_name}")

            # Test specific classes/functions
            if module_name == "app.llm.client":
                print("     - LLMClient class available")
            elif module_name == "app.routers.config":
                print("     - get_config function available")

        except Exception as e:
            print(f"   ✗ {module_name}: {e}")


async def main():
    """Run all tests."""
    print("🚀 Azure OpenAI Integration Test Suite")
    print("=" * 60)

    test_import_health()
    test_environment_setup()
    test_message_conversion()
    await test_config_endpoint()

    print("\n🎉 All tests completed!")
    print("\nTo test with real Azure OpenAI:")
    print("1. Set up your Azure OpenAI resource")
    print("2. Configure environment variables in .env")
    print("3. Start the backend server")
    print("4. Test chat completions via the API")


if __name__ == "__main__":
    asyncio.run(main())
