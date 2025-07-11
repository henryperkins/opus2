#!/usr/bin/env python3
"""Test script to verify the AI config update endpoint."""

import asyncio
import json
import httpx
from typing import Dict, Any

# Configuration
BASE_URL = "https://lakefrontdigital.io"
ENDPOINT = "/api/v1/ai-config"

# Your authentication token (you'll need to get this from your browser)
# In browser console: localStorage.getItem('token')
AUTH_TOKEN = "YOUR_AUTH_TOKEN_HERE"  # Replace with actual token


async def test_config_update():
    """Test the configuration update endpoint."""
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
    }

    # Test payload - exactly what the frontend sends
    payload = {
        "modelId": "gpt-4o",
        "provider": "openai",
        "temperature": 0.7
    }

    print("Testing AI Config Update Endpoint")
    print("="*50)
    print(f"URL: {BASE_URL}{ENDPOINT}")
    print(f"Method: PATCH")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("="*50)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(
                f"{BASE_URL}{ENDPOINT}",
                headers=headers,
                json=payload,
                timeout=30.0
            )

            print(f"\nStatus Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")

            try:
                response_data = response.json()
                print(f"\nResponse Body: {json.dumps(response_data, indent=2)}")
            except:
                print(f"\nRaw Response: {response.text}")

            if response.status_code != 200:
                print("\n❌ Error: Request failed")

                # Try to debug the error
                if response.status_code == 422:
                    print("\n🔍 Validation Error Details:")
                    if isinstance(response_data, dict) and "detail" in response_data:
                        detail = response_data["detail"]
                        if isinstance(detail, list):
                            for error in detail:
                                print(f"  - Field: {error.get('loc', ['unknown'])}")
                                print(f"    Type: {error.get('type', 'unknown')}")
                                print(f"    Message: {error.get('msg', 'no message')}")
                        else:
                            print(f"  - {detail}")
            else:
                print("\n✅ Success: Configuration updated")

        except Exception as e:
            print(f"\n❌ Exception: {type(e).__name__}: {e}")


async def test_get_config():
    """Test getting the current configuration."""
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
    }

    print("\n\nTesting AI Config GET Endpoint")
    print("="*50)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}{ENDPOINT}",
                headers=headers,
                timeout=30.0
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"\nCurrent Config: {json.dumps(data, indent=2)}")
            else:
                print(f"\nError: {response.text}")

        except Exception as e:
            print(f"\n❌ Exception: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("AI Config API Test Script")
    print("Make sure to set AUTH_TOKEN before running!")

    # Run tests
    asyncio.run(test_get_config())
    asyncio.run(test_config_update())
