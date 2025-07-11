#!/usr/bin/env python3
"""
Debug authentication issues by testing the JWT decoding directly.
"""
import sys
sys.path.insert(0, '/app')

from app.auth import security
from app.database import SessionLocal
from app.models.user import User
from app.auth.utils import is_session_active
import jwt

def debug_jwt_decoding():
    """Test JWT decoding directly."""
    
    # This is the JWT from the test
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaWF0IjoxNzUyMjIzOTQwLCJleHAiOjE3NTIzMTAzNDAsImp0aSI6Imo3aFBBZkxrQWR5V0JScE4tdmpWSFFBMXVSUEdrVTlJTy1TeldBTWRrWWMifQ.LKZKFOsBxQRzFTpnj1eRbXDtJqyJPYjjTyYNQvhp-hQ"
    
    print("🔍 Debugging JWT Authentication...")
    
    with SessionLocal() as db:
        try:
            # 1. Test JWT decoding
            print(f"\n1. Testing JWT decoding...")
            payload = security.decode_access_token(token)
            print(f"   ✅ JWT decoded successfully: {payload}")
            
            # 2. Test user ID extraction
            print(f"\n2. Testing user ID extraction...")
            user_id = security.token_sub_identity(payload)
            print(f"   ✅ User ID extracted: {user_id}")
            
            # 3. Test session validation
            print(f"\n3. Testing session validation...")
            jti = payload.get("jti")
            if jti:
                session_active = is_session_active(db, jti)
                print(f"   Session active: {session_active}")
            else:
                print("   No JTI in payload")
            
            # 4. Test user lookup
            print(f"\n4. Testing user lookup...")
            user = db.get(User, user_id)
            if user:
                print(f"   ✅ User found: {user.username} (active: {user.is_active})")
            else:
                print(f"   ❌ User not found for ID: {user_id}")
            
            # 5. Test full authentication flow
            print(f"\n5. Testing full authentication flow...")
            from app.auth.utils import get_current_user
            from fastapi import Request
            
            # Mock request with cookie
            class MockRequest:
                def __init__(self, cookies):
                    self.cookies = cookies
                    self.headers = {}
            
            mock_request = MockRequest({"access_token": token})
            
            try:
                authenticated_user = get_current_user(
                    request=mock_request,
                    db=db,
                    authorization=None,
                    access_cookie=token
                )
                print(f"   ✅ Full auth flow successful: {authenticated_user.username}")
            except Exception as e:
                print(f"   ❌ Full auth flow failed: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"   ❌ JWT processing failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_jwt_decoding()