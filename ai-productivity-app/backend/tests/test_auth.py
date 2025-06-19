"""
Comprehensive authentication tests for Phase 2.

Tests cover:
" User registration with valid/invalid data
" Login with correct/incorrect credentials  
" Protected endpoint access
" Token expiration handling
" Password reset flow
" Rate limiting
" CSRF protection
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.auth import security
from app.models.user import User
from app.config import settings
import time


client = TestClient(app)


@pytest.fixture
def test_user_data():
    """Standard test user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }


@pytest.fixture
def test_user(db: Session, test_user_data):
    """Create a test user in the database."""
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        password_hash=security.hash_password(test_user_data["password"])
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestUserRegistration:
    """Test user registration functionality."""

    def test_register_success(self, db: Session):
        """Test successful user registration."""
        data = {
            "username": "newuser",
            "email": "new@example.com", 
            "password": "password123"
        }
        response = client.post("/api/auth/register", json=data)
        
        assert response.status_code == 201
        result = response.json()
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert "expires_in" in result
        
        # Verify user was created in database
        user = db.query(User).filter(User.username == "newuser").first()
        assert user is not None
        assert user.email == "new@example.com"
        assert user.is_active is True


    def test_register_duplicate_username(self, test_user):
        """Test registration with existing username."""
        data = {
            "username": test_user.username,
            "email": "different@example.com",
            "password": "password123"
        }
        response = client.post("/api/auth/register", json=data)
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_register_duplicate_email(self, test_user):
        """Test registration with existing email."""
        data = {
            "username": "differentuser",
            "email": test_user.email,
            "password": "password123"
        }
        response = client.post("/api/auth/register", json=data)
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_register_invalid_password(self):
        """Test registration with invalid password."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "short"  # Too short
        }
        response = client.post("/api/auth/register", json=data)
        
        assert response.status_code == 422  # Validation error

    def test_register_invalid_email(self):
        """Test registration with invalid email."""
        data = {
            "username": "newuser",
            "email": "not-an-email",
            "password": "password123"
        }
        response = client.post("/api/auth/register", json=data)
        
        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """Test user login functionality."""

    def test_login_success_username(self, test_user, test_user_data):
        """Test successful login with username."""
        data = {
            "username_or_email": test_user_data["username"],
            "password": test_user_data["password"]
        }
        response = client.post("/api/auth/login", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        
        # Check that auth cookie was set
        assert "access_token" in response.cookies

    def test_login_success_email(self, test_user, test_user_data):
        """Test successful login with email."""
        data = {
            "username_or_email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/api/auth/login", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert "access_token" in result

    def test_login_invalid_credentials(self, test_user):
        """Test login with invalid credentials."""
        data = {
            "username_or_email": test_user.username,
            "password": "wrongpassword"
        }
        response = client.post("/api/auth/login", json=data)
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self):
        """Test login with non-existent user."""
        data = {
            "username_or_email": "nonexistent",
            "password": "password123"
        }
        response = client.post("/api/auth/login", json=data)
        
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]


class TestProtectedEndpoints:
    """Test protected endpoint access."""

    def get_auth_headers(self, test_user):
        """Helper to get authorization headers."""
        token = security.create_access_token({"sub": str(test_user.id)})
        return {"Authorization": f"Bearer {token}"}

    def test_me_endpoint_authenticated(self, test_user):
        """Test /me endpoint with valid authentication."""
        headers = self.get_auth_headers(test_user)
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == test_user.id
        assert result["username"] == test_user.username
        assert result["email"] == test_user.email
        assert result["is_active"] is True

    def test_me_endpoint_unauthenticated(self):
        """Test /me endpoint without authentication."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_me_endpoint_invalid_token(self):
        """Test /me endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalidtoken"}
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 401

    def test_me_endpoint_expired_token(self, test_user):
        """Test /me endpoint with expired token."""
        # Create an expired token (negative expiration)
        from datetime import timedelta
        token = security.create_access_token(
            {"sub": str(test_user.id)},
            expires_delta=timedelta(seconds=-1)
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        time.sleep(1)  # Ensure token is expired
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == 401

    def test_me_endpoint_with_cookie(self, test_user):
        """Test /me endpoint with auth cookie."""
        token = security.create_access_token({"sub": str(test_user.id)})
        cookies = {"access_token": token}
        response = client.get("/api/auth/me", cookies=cookies)
        
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == test_user.id


class TestLogout:
    """Test logout functionality."""

    def test_logout_success(self):
        """Test successful logout."""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 204
        
        # Check that auth cookie was cleared
        assert "access_token" in response.cookies
        # Cookie should be cleared (empty value)
        assert response.cookies["access_token"] == ""


class TestPasswordReset:
    """Test password reset functionality."""

    def test_request_password_reset(self, test_user):
        """Test password reset request."""
        data = {"email": test_user.email}
        response = client.post("/api/auth/reset-password", json=data)
        
        assert response.status_code == 202
        assert "instructions sent" in response.json()["detail"]

    def test_request_password_reset_nonexistent_email(self):
        """Test password reset request for non-existent email."""
        data = {"email": "nonexistent@example.com"}
        response = client.post("/api/auth/reset-password", json=data)
        
        # Should still return 202 for security (don't reveal if email exists)
        assert response.status_code == 202

    def test_submit_password_reset_success(self, test_user, db: Session):
        """Test successful password reset submission."""
        # Create a reset token
        from datetime import timedelta
        token = security.create_access_token(
            {"sub": test_user.email, "purpose": "reset"},
            expires_delta=timedelta(minutes=30)
        )
        
        data = {
            "token": token,
            "new_password": "newpassword123"
        }
        response = client.post("/api/auth/reset-password/submit", json=data)
        
        assert response.status_code == 204
        
        # Verify password was updated
        db.refresh(test_user)
        assert security.verify_password("newpassword123", test_user.password_hash)

    def test_submit_password_reset_invalid_token(self):
        """Test password reset submission with invalid token."""
        data = {
            "token": "invalidtoken",
            "new_password": "newpassword123"
        }
        response = client.post("/api/auth/reset-password/submit", json=data)
        
        assert response.status_code == 401

    def test_submit_password_reset_wrong_purpose(self, test_user):
        """Test password reset submission with wrong purpose token."""
        # Create regular token (not reset purpose)
        token = security.create_access_token({"sub": test_user.email})
        
        data = {
            "token": token,
            "new_password": "newpassword123"
        }
        response = client.post("/api/auth/reset-password/submit", json=data)
        
        assert response.status_code == 400
        assert "Invalid reset token" in response.json()["detail"]


class TestSecurityFeatures:
    """Test security features like rate limiting and CSRF."""

    def test_rate_limiting_register(self):
        """Test rate limiting on registration endpoint."""
        data = {
            "username": "spammer",
            "email": "spam@example.com",
            "password": "password123"
        }
        
        # Make multiple requests quickly (should hit rate limit)
        responses = []
        for i in range(10):
            response = client.post("/api/auth/register", json={
                **data,
                "username": f"spammer{i}",
                "email": f"spam{i}@example.com"
            })
            responses.append(response)
        
        # Should get at least one 429 response
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes

    def test_rate_limiting_login(self, test_user):
        """Test rate limiting on login endpoint."""
        data = {
            "username_or_email": test_user.username,
            "password": "wrongpassword"
        }
        
        # Make multiple failed login attempts
        responses = []
        for _ in range(10):
            response = client.post("/api/auth/login", json=data)
            responses.append(response)
        
        # Should get at least one 429 response
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes


class TestTokenValidation:
    """Test JWT token validation."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = security.hash_password(password)
        
        assert hashed != password
        assert security.verify_password(password, hashed)
        assert not security.verify_password("wrongpassword", hashed)

    def test_token_creation_and_validation(self, test_user):
        """Test JWT token creation and validation."""
        token = security.create_access_token({"sub": str(test_user.id)})
        
        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Should be able to decode it
        payload = security.decode_access_token(token)
        assert payload["sub"] == str(test_user.id)
        assert "exp" in payload
        assert "iat" in payload

    def test_csrf_token_generation(self):
        """Test CSRF token generation."""
        token1 = security.generate_csrf_token()
        token2 = security.generate_csrf_token()
        
        # Tokens should be different
        assert token1 != token2
        assert len(token1) > 0
        assert len(token2) > 0


class TestUserModel:
    """Test User model validation."""

    def test_username_validation(self, db: Session):
        """Test username validation."""
        # Valid username
        user = User(
            username="validuser",
            email="valid@example.com",
            password_hash="hash"
        )
        assert user.username == "validuser"
        
        # Username should be lowercased
        user.username = "UpperCase"
        assert user.username == "uppercase"

    def test_email_validation(self, db: Session):
        """Test email validation.""" 
        user = User(
            username="testuser",
            email="Test@Example.COM",
            password_hash="hash"
        )
        # Email should be lowercased
        assert user.email == "test@example.com"