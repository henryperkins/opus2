#!/usr/bin/env python3
"""Test script to debug AI config endpoint issues."""

import asyncio
import httpx
import sys

async def test_ai_config_endpoint():
    """Test the AI config endpoint directly."""

    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    async with httpx.AsyncClient() as client:
        # First, check if we're authenticated
        try:
            print("1. Testing authentication status...")
            me_response = await client.get(
                f"{base_url}/api/auth/me",
                cookies={"access_token": "test_token_1"}  # Using test token
            )
            print(f"   Auth status: {me_response.status_code}")
            if me_response.status_code == 200:
                print(f"   User: {me_response.json()}")
            else:
                print(f"   Error: {me_response.text}")
        except Exception as e:
            print(f"   Auth check failed: {e}")

        # Now test the AI config endpoint
        try:
            print("\n2. Testing AI config endpoint...")
            config_response = await client.get(
                f"{base_url}/api/v1/ai-config",
                cookies={"access_token": "test_token_1"}  # Using test token
            )
            print(f"   Status: {config_response.status_code}")

            if config_response.status_code == 200:
                data = config_response.json()
                print(f"   Response keys: {list(data.keys())}")
            else:
                print(f"   Error response: {config_response.text}")

                # Try to parse error details
                try:
                    error_data = config_response.json()
                    if "detail" in error_data:
                        print(f"   Error detail: {error_data['detail']}")
                except:
                    pass

        except Exception as e:
            print(f"   Config endpoint failed: {e}")

        # Test the simpler test endpoint
        try:
            print("\n3. Testing simple test endpoint...")
            test_response = await client.get(
                f"{base_url}/api/v1/ai-config/test"
            )
            print(f"   Status: {test_response.status_code}")
            print(f"   Response: {test_response.json()}")
        except Exception as e:
            print(f"   Test endpoint failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_config_endpoint())
