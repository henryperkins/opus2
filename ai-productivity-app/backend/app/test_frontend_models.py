#!/usr/bin/env python3
"""
Test script to verify models are accessible for frontend integration.
"""
import os
import sys
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to Python path
sys.path.insert(0, "/app")

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.config import ModelConfiguration
from app.auth.dependencies import get_current_user
from app.utils.security import get_password_hash

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def get_test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the get_db dependency
app.dependency_overrides[get_db] = get_test_db


# Create test user
def create_test_user():
    db = TestingSessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if existing_user:
            return existing_user

        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("testpass"),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


# Create test models
def create_test_models():
    db = TestingSessionLocal()
    try:
        # Check if models already exist
        existing_models = db.query(ModelConfiguration).count()
        if existing_models > 0:
            return

        # Add a few test models
        test_models = [
            ModelConfiguration(
                model_id="gpt-4o-mini",
                provider="openai",
                model_family="gpt-4",
                display_name="GPT-4 Mini",
                is_available=True,
                is_deprecated=False,
                capabilities={"supports_vision": True, "supports_functions": True},
                cost_input_per_1k=0.15,
                cost_output_per_1k=0.60,
            ),
            ModelConfiguration(
                model_id="o3-mini",
                provider="openai",
                model_family="o3",
                display_name="O3 Mini",
                is_available=True,
                is_deprecated=False,
                capabilities={"supports_reasoning": True, "supports_functions": False},
                cost_input_per_1k=0.15,
                cost_output_per_1k=0.60,
            ),
            ModelConfiguration(
                model_id="claude-sonnet-4-20250514",
                provider="anthropic",
                model_family="claude-4",
                display_name="Claude 4 Sonnet",
                is_available=True,
                is_deprecated=False,
                capabilities={
                    "supports_vision": True,
                    "supports_functions": True,
                    "supports_thinking": True,
                },
                cost_input_per_1k=3.0,
                cost_output_per_1k=15.0,
            ),
        ]

        for model in test_models:
            db.add(model)
        db.commit()
        print(f"Created {len(test_models)} test models")
    finally:
        db.close()


def test_models_endpoint():
    """Test the models endpoint to verify it works."""
    client = TestClient(app)

    # Create test user and models
    test_user = create_test_user()
    create_test_models()

    # Override auth dependency for testing
    def get_current_user_override():
        return test_user

    app.dependency_overrides[get_current_user] = get_current_user_override

    try:
        # Test models endpoint
        response = client.get("/api/v1/ai-config/models")
        print(f"Models endpoint status: {response.status_code}")

        if response.status_code == 200:
            models = response.json()
            print(f"Found {len(models)} models:")
            for model in models:
                print(f"  - {model['modelId']} ({model['provider']})")
            return True
        else:
            print(f"Error: {response.json()}")
            return False

    except Exception as e:
        print(f"Exception: {e}")
        return False


def test_config_endpoint():
    """Test the main config endpoint."""
    client = TestClient(app)

    try:
        # Test main config endpoint
        response = client.get("/api/v1/ai-config")
        print(f"Config endpoint status: {response.status_code}")

        if response.status_code == 200:
            config = response.json()
            print(
                f"Current config: {config.get('current', {}).get('modelId', 'Not set')}"
            )
            available_models = config.get("availableModels", [])
            print(f"Available models in config: {len(available_models)}")
            return True
        else:
            print(f"Error: {response.json()}")
            return False

    except Exception as e:
        print(f"Exception: {e}")
        return False


if __name__ == "__main__":
    print("🔍 Testing Frontend Models Integration...")

    models_ok = test_models_endpoint()
    config_ok = test_config_endpoint()

    if models_ok and config_ok:
        print("✅ All tests passed! Models should be accessible in frontend.")
    else:
        print("❌ Some tests failed. Models may not be accessible in frontend.")
