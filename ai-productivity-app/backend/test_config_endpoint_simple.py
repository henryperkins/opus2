#!/usr/bin/env python3
"""Simple test to verify the AI config update endpoint works."""

import requests
import json

# Replace with your actual auth token
AUTH_TOKEN = "YOUR_AUTH_TOKEN_HERE"

# Base URL
BASE_URL = "https://lakefrontdigital.io"

# Create a session to handle cookies
session = requests.Session()

# First, get the CSRF token by making a GET request
print("Getting CSRF token...")
auth_headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
}

try:
    # Make initial request to get CSRF cookie
    response = session.get(f"{BASE_URL}/api/v1/ai-config", headers=auth_headers, timeout=30)

    # Extract CSRF token from cookies
    csrf_token = session.cookies.get('csrftoken', '')
    print(f"CSRF Token obtained: {csrf_token[:20]}..." if csrf_token else "No CSRF token found")

    # Test data
    test_payload = {
        "modelId": "gpt-4o",
        "provider": "openai",
        "temperature": 0.7
    }

    # Make the PATCH request with CSRF token
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
        "X-CSRFToken": csrf_token  # Add CSRF token header
    }

    url = f"{BASE_URL}/api/v1/ai-config"

    print(f"\nTesting PATCH {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")

    response = session.patch(url, headers=headers, json=test_payload, timeout=30)

    print(f"\nStatus Code: {response.status_code}")

    try:
        response_data = response.json()
        print(f"Response: {json.dumps(response_data, indent=2)}")
    except:
        print(f"Raw Response: {response.text[:500]}...")

    if response.status_code == 200:
        print("\n✅ Success! The endpoint is working correctly.")
    else:
        print("\n❌ Error: The endpoint returned an error.")
        if response.status_code == 403:
            print("Note: CSRF protection is active. The frontend handles this automatically.")

except Exception as e:
    print(f"\n❌ Exception: {type(e).__name__}: {e}")

# Also test GET endpoint
print("\n" + "="*50)
print("Testing GET endpoint to verify current config...")

try:
    response = requests.get(url, headers={"Authorization": f"Bearer {AUTH_TOKEN}"}, timeout=30)

    if response.status_code == 200:
        data = response.json()
        current_config = data.get("current", {})
        print(f"\nCurrent config:")
        print(f"  Model ID: {current_config.get('modelId')}")
        print(f"  Provider: {current_config.get('provider')}")
        print(f"  Temperature: {current_config.get('temperature')}")
    else:
        print(f"\nError: {response.status_code} - {response.text}")

except Exception as e:
    print(f"\n❌ Exception: {type(e).__name__}: {e}")
