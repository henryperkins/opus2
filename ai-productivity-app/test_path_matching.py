#!/usr/bin/env python3

"""Test the path matching logic for OPTIONS wildcards directly."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.auth.security import FastAPI

def test_path_matching():
    """Test that the _match method handles path wildcards correctly."""
    app = FastAPI()
    
    # Register a test handler
    def test_handler(rest_of_path: str):
        return f"path: {rest_of_path}"
    
    app.routes.append(("OPTIONS", "/api/{rest_of_path:path}", test_handler))
    
    # Test various paths
    test_cases = [
        ("/api/auth/register", "auth/register"),
        ("/api/auth/login", "auth/login"), 
        ("/api/projects", "projects"),
        ("/api/projects/123/timeline", "projects/123/timeline"),
        ("/api/search/code", "search/code")
    ]
    
    print("Testing path matching with wildcard routes...")
    
    for path, expected_rest in test_cases:
        handler, path_params, query_params = app._match("OPTIONS", path)
        
        if handler is None:
            print(f"❌ FAILED: {path} -> No handler found")
            return False
        
        if "rest_of_path" not in path_params:
            print(f"❌ FAILED: {path} -> Missing rest_of_path parameter")
            return False
            
        actual_rest = path_params["rest_of_path"]
        if actual_rest != expected_rest:
            print(f"❌ FAILED: {path} -> Expected '{expected_rest}', got '{actual_rest}'")
            return False
        
        print(f"✅ {path} -> {actual_rest}")
    
    print("✅ All path matching tests passed!")
    return True

if __name__ == "__main__":
    success = test_path_matching()
    sys.exit(0 if success else 1)