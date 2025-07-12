#!/usr/bin/env python3
import requests
import json

try:
    response = requests.get("http://localhost:8000/api/v1/ai-config")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")

    if response.headers.get('content-type', '').startswith('application/json'):
        try:
            json_data = response.json()
            print(f"JSON Response: {json.dumps(json_data, indent=2)}")
        except json.JSONDecodeError:
            print("Failed to parse JSON response")

except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
