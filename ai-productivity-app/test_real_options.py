#!/usr/bin/env python3

"""Test actual OPTIONS requests on the FastAPI app."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

import httpx
from app.main import app

def test_real_options():
    """Test OPTIONS requests to various endpoints."""
    # Test OPTIONS requests to various endpoints
    test_paths = ['/api/auth/register', '/api/auth/login', '/api/projects']

    print("Testing real OPTIONS requests...")
    
    with httpx.Client(app=app, base_url="http://test") as client:
        for path in test_paths:
            response = client.request("OPTIONS", path)
            print(f'OPTIONS {path}: {response.status_code}')
            if response.status_code != 200:
                print(f'  Headers: {dict(response.headers)}')
                print(f'  Content: {response.content}')
                return False
    
    print("✅ All OPTIONS requests succeeded!")
    return True

if __name__ == "__main__":
    success = test_real_options()
    sys.exit(0 if success else 1)