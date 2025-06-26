#!/usr/bin/env python3
"""
Test script to validate the config endpoint returns proper HTTP status codes.
This ensures the 500-retry loop fix is working correctly.
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, Any

# Test configurations
VALID_CONFIG = {
    "provider": "openai",
    "chat_model": "gpt-4o-mini",
    "temperature": 0.7
}

INVALID_CONFIG = {
    "provider": "invalid_provider",
    "chat_model": "nonexistent_model",
    "temperature": 2.5  # Invalid temperature > 2.0
}

MALFORMED_CONFIG = {
    "provider": None,
    "chat_model": "",
    "temperature": "not_a_number"
}

async def test_config_endpoint(base_url: str = "http://localhost:8000"):
    """Test the /api/config/model endpoint with various payloads."""

    async with httpx.AsyncClient() as client:
        print(f"Testing config endpoint at {base_url}")

        # Test 1: Valid configuration should succeed (200)
        print("\n1. Testing valid configuration...")
        try:
            response = await client.put(
                f"{base_url}/api/config/model",
                json=VALID_CONFIG,
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print("   ✓ Valid config accepted")
        except Exception as e:
            print(f"   ✗ Valid config failed: {e}")

        # Test 2: Invalid configuration should return 422 (not 500)
        print("\n2. Testing invalid configuration...")
        try:
            response = await client.put(
                f"{base_url}/api/config/model",
                json=INVALID_CONFIG,
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            assert response.status_code == 422, f"Expected 422, got {response.status_code}"
            print("   ✓ Invalid config properly rejected with 422")
        except Exception as e:
            print(f"   ✗ Invalid config test failed: {e}")

        # Test 3: Malformed configuration should return 422 (not 500)
        print("\n3. Testing malformed configuration...")
        try:
            response = await client.put(
                f"{base_url}/api/config/model",
                json=MALFORMED_CONFIG,
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            assert response.status_code in [400, 422], f"Expected 400 or 422, got {response.status_code}"
            print("   ✓ Malformed config properly rejected with 4xx")
        except Exception as e:
            print(f"   ✗ Malformed config test failed: {e}")

        # Test 4: Empty payload should return 400
        print("\n4. Testing empty configuration...")
        try:
            response = await client.put(
                f"{base_url}/api/config/model",
                json={},
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            print("   ✓ Empty config properly rejected with 400")
        except Exception as e:
            print(f"   ✗ Empty config test failed: {e}")

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    asyncio.run(test_config_endpoint(base_url))
