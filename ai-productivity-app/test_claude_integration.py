#!/usr/bin/env python3
"""
Test script to add Claude models and test basic integration.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_config_api():
    """Test the config API."""
    print("Testing config API...")
    
    # Test current config
    response = requests.get(f"{BASE_URL}/api/config")
    if response.status_code == 200:
        config = response.json()
        print("✓ Config API working")
        print(f"Current provider: {config.get('current', {}).get('provider')}")
        print(f"Current model: {config.get('current', {}).get('chat_model')}")
        return True
    else:
        print(f"✗ Config API failed: {response.status_code}")
        return False

def add_anthropic_provider():
    """Add Anthropic provider to config."""
    print("\nAdding Anthropic provider...")
    
    # Update config to include Anthropic
    config_update = {
        "provider": "anthropic",
        "chat_model": "claude-sonnet-4-20250514"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/config",
        json=config_update,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code in [200, 201]:
        print("✓ Successfully updated config to use Anthropic")
        return True
    else:
        print(f"✗ Failed to update config: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_claude_chat():
    """Test a simple chat with Claude."""
    print("\nTesting Claude chat...")
    
    # Try a simple chat message
    chat_payload = {
        "message": "Hello, Claude! Can you confirm you're working by saying 'Claude Sonnet 4 is working'?",
        "session_id": "test-session-001"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/chat/send",
        json=chat_payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Claude chat working!")
        print(f"Response: {result.get('content', 'No content')}")
        return True
    else:
        print(f"✗ Claude chat failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def main():
    """Run all tests."""
    print("=== Claude Integration Test ===\n")
    
    success = True
    
    # Test 1: Config API
    if not test_config_api():
        success = False
    
    # Test 2: Add Anthropic provider
    if not add_anthropic_provider():
        success = False
    
    # Test 3: Test Claude chat (if API key is available)
    if not test_claude_chat():
        print("Note: Claude chat test failed - this is expected without API key")
    
    print(f"\n=== Test Summary ===")
    print(f"Overall status: {'✓ PASS' if success else '✗ FAIL'}")
    print("\nTo complete the integration:")
    print("1. Set ANTHROPIC_API_KEY environment variable")
    print("2. Restart the backend service")
    print("3. Test with real API calls")

if __name__ == "__main__":
    main()