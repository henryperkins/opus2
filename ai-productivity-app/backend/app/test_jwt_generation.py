#!/usr/bin/env python3
"""
Test JWT generation and verification with current configuration.
"""
import sys

sys.path.insert(0, "/app")

from app.auth import security
from app.config import settings
from datetime import datetime, timedelta, timezone


def test_jwt_generation():
    """Test JWT generation and verification."""

    print("🔍 Testing JWT Generation...")

    # Create a test payload
    payload = {"sub": "1", "jti": "test-jti"}

    print(f"\n1. Configuration:")
    print(f"   SECRET_KEY: {settings.secret_key}")
    print(f"   JWT_SECRET_KEY: {settings.jwt_secret_key}")
    print(f"   EFFECTIVE_SECRET_KEY: {settings.effective_secret_key}")
    print(f"   Algorithm: {settings.algorithm}")

    print(f"\n2. Creating JWT token...")
    try:
        token = security.create_access_token(payload)
        print(f"   ✅ JWT created: {token[:50]}...")

        print(f"\n3. Verifying JWT token...")
        decoded = security.decode_access_token(token)
        print(f"   ✅ JWT verified: {decoded}")

        return token

    except Exception as e:
        print(f"   ❌ JWT generation/verification failed: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_jwt_generation()
