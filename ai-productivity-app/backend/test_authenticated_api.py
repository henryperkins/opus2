#!/usr/bin/env python3
"""
Test authenticated API access for models endpoint.
"""
import requests
import json

def test_authenticated_models_access():
    """Test models endpoint with proper authentication."""
    
    base_url = "http://localhost:8000"
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("🔍 Testing Authenticated Models Access...")
    
    # 1. Login with provided credentials (no CSRF needed for login)
    print("\n1. Logging in...")
    login_data = {
        "username": "hperkins", 
        "password": "Twiohmld1234!"
    }
    
    login_response = session.post(
        f"{base_url}/api/auth/login",
        json=login_data
    )
    
    print(f"   Login status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"   ❌ Login failed: {login_response.text}")
        return False
    
    print("   ✅ Login successful!")
    
    # Check what cookies were set
    print("   Cookies after login:")
    for cookie in session.cookies:
        print(f"     {cookie.name}: {cookie.value[:20]}... (domain: {cookie.domain}, path: {cookie.path})")
    
    # Check login response headers
    print("   Login response headers:")
    for header, value in login_response.headers.items():
        if 'cookie' in header.lower():
            print(f"     {header}: {value}")
    
    # Fix cookie domain issue by creating a new cookie with correct domain
    access_token_value = None
    for cookie in session.cookies:
        if cookie.name == 'access_token':
            print(f"   Original cookie domain: {cookie.domain}")
            access_token_value = cookie.value
            break
    
    # Create a new session with the correct cookie domain
    session.cookies.clear()
    session.cookies.set('access_token', access_token_value, domain='localhost', path='/')
    print(f"   Fixed cookie domain to: localhost")
    
    # 2. Test models endpoint
    print("\n2. Testing models endpoint...")
    
    # Debug: Check what's in the JWT token
    import jwt
    access_token = None
    for cookie in session.cookies:
        if cookie.name == 'access_token':
            access_token = cookie.value
            break
    
    if access_token:
        try:
            # Decode without verification to see payload
            decoded = jwt.decode(access_token, options={"verify_signature": False})
            print(f"   JWT payload: {decoded}")
        except Exception as e:
            print(f"   JWT decode error: {e}")
    
    # Debug: Show what cookies are being sent
    print(f"   Cookies being sent: {session.cookies}")
    
    # Test with automatic cookie handling (should work now)
    models_response = session.get(f"{base_url}/api/v1/ai-config/models")
    
    print(f"   Models status: {models_response.status_code}")
    
    # Debug: Show request headers
    print(f"   Request headers: {dict(models_response.request.headers)}")
    
    if models_response.status_code == 200:
        models = models_response.json()
        print(f"   ✅ Found {len(models)} models:")
        
        # Show first few models
        for i, model in enumerate(models[:5]):
            print(f"      {i+1}. {model['modelId']} ({model['provider']})")
        
        # Check for latest models
        latest_models = [
            'o4-mini', 'o3', 'o3-mini', 'o3-pro',
            'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-4.5',
            'claude-opus-4-20250514', 'claude-sonnet-4-20250514'
        ]
        
        model_ids = [m['modelId'] for m in models]
        print(f"\n   Latest models check:")
        for model_id in latest_models:
            status = "✅" if model_id in model_ids else "❌"
            print(f"      {status} {model_id}")
        
        return True
    else:
        print(f"   ❌ Models endpoint failed: {models_response.text}")
        return False
    
    # 3. Test main config endpoint
    print("\n3. Testing main config endpoint...")
    config_response = session.get(f"{base_url}/api/v1/ai-config")
    print(f"   Config status: {config_response.status_code}")
    
    if config_response.status_code == 200:
        config = config_response.json()
        current_model = config.get('current', {}).get('modelId', 'Not set')
        available_models = config.get('availableModels', [])
        print(f"   ✅ Current model: {current_model}")
        print(f"   ✅ Available models: {len(available_models)}")
        return True
    else:
        print(f"   ❌ Config endpoint failed: {config_response.text}")
        return False

if __name__ == "__main__":
    success = test_authenticated_models_access()
    
    if success:
        print("\n🎉 SUCCESS: Models are accessible when authenticated!")
        print("   The issue may be with frontend authentication state.")
    else:
        print("\n❌ FAILURE: Models are not accessible even when authenticated.")
        print("   The issue may be with the backend API implementation.")