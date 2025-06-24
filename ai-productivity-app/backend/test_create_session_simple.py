#!/usr/bin/env python3
"""
Simple test to verify the create_session function works correctly.
"""

from app.auth import utils
from app.models.session import Session


class MockDB:
    """Mock database session for testing."""

    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


class MockUser:
    """Mock user for testing."""
    id = 1


def test_create_session():
    """Test that create_session function works correctly."""
    print("Testing create_session function...")

    # Check that function exists
    assert hasattr(utils, 'create_session'), "create_session function not found in utils module"
    print("✓ create_session function exists")

    # Test function signature
    import inspect
    sig = inspect.signature(utils.create_session)
    expected_params = ['db', 'user', 'jti', 'ttl_minutes']
    actual_params = list(sig.parameters.keys())
    assert actual_params == expected_params, f"Expected params {expected_params}, got {actual_params}"
    print("✓ Function signature is correct")

    # Test function with mock objects
    user = MockUser()
    db = MockDB()
    jti = 'test-jti-123'

    # This should create a session without errors
    session = utils.create_session(db, user, jti, 60)

    # Verify session properties
    assert session.user_id == user.id, f"Expected user_id {user.id}, got {session.user_id}"
    assert session.jti == jti, f"Expected jti {jti}, got {session.jti}"
    print("✓ Session created with correct properties")

    # Verify DB operations were called
    assert len(db.added) == 1, f"Expected 1 object added to DB, got {len(db.added)}"
    assert db.committed, "Expected DB commit to be called"
    assert len(db.refreshed) == 1, f"Expected 1 object refreshed, got {len(db.refreshed)}"
    print("✓ Database operations called correctly")

    print("\n🎉 All tests passed! The create_session function is working correctly.")
    return True


if __name__ == "__main__":
    try:
        test_create_session()
        print("\n✅ SUCCESS: create_session function is properly implemented and working!")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
