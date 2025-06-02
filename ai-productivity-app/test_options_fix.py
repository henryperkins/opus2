#!/usr/bin/env python3

"""Test script to verify OPTIONS route matching works."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.auth.security import TestClient

def test_options_route_matching():
    """Test that OPTIONS routes with path wildcards work correctly."""
    from app.auth.security import FastAPI
    app = FastAPI()
    client = TestClient(app)
    
    # Register the OPTIONS route with path wildcard
    @client.options("/api/{rest_of_path:path}")
    def cors_preflight(rest_of_path: str):
        return {"status": "ok", "path": rest_of_path}
    
    # Test that it matches various paths
    test_paths = [
        "/api/auth/register",
        "/api/auth/login", 
        "/api/projects",
        "/api/projects/123/timeline",
        "/api/search/code"
    ]
    
    for path in test_paths:
        print(f"Testing OPTIONS {path}")
        response = client.options(path)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {data}")
            expected_rest = path.replace("/api/", "")
            assert data["path"] == expected_rest, f"Expected path '{expected_rest}', got '{data['path']}'"
        else:
            print(f"  FAILED: Expected 200, got {response.status_code}")
            return False
    
    print("✅ All OPTIONS route tests passed!")
    return True

if __name__ == "__main__":
    success = test_options_route_matching()
    sys.exit(0 if success else 1)