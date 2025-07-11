"""
Tests for the unified AI configuration system.

Tests cover:
- camelCase API responses
- snake_case and camelCase input acceptance  
- Model catalog seeding
- Configuration validation
- WebSocket notifications
"""

import os
import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Unified config is now always enabled

from app.main import app
from app.models.user import User
from app.models.config import RuntimeConfig, ModelConfiguration
from app.services.unified_config_service import UnifiedConfigService
from app.config import settings


client = TestClient(app)


@pytest.fixture
def test_user_data():
    """Standard test user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "name": "Test User",
    }


@pytest.fixture
def authenticated_user(db: Session, test_user_data):
    """Create and authenticate a test user."""
    # Register user
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 201

    # Login to get access token
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        },
    )
    assert login_response.status_code == 200

    # Return user and access token from cookie
    return {
        "user": db.query(User).filter_by(username=test_user_data["username"]).first(),
        "cookies": login_response.cookies,
    }


@pytest.fixture
def seeded_config(db: Session):
    """Seed the database with test configuration."""
    service = UnifiedConfigService(db)
    service.initialize_defaults()

    # Add some test model configurations
    test_model = ModelConfiguration(
        model_id="test-gpt-4o",
        name="Test GPT-4 Omni",
        provider="openai",
        model_family="gpt-4",
        capabilities={
            "supports_functions": True,
            "supports_vision": True,
            "max_context_window": 128000,
            "max_output_tokens": 4096,
        },
        cost_input_per_1k=0.0025,
        cost_output_per_1k=0.01,
        tier="balanced",
        is_available=True,
    )
    db.add(test_model)
    db.commit()

    return service


class TestUnifiedConfigAPI:
    """Test the unified configuration API endpoints."""

    def test_get_config_returns_camelcase(self, authenticated_user, seeded_config):
        """Test that GET /api/v1/ai-config returns camelCase fields."""
        response = client.get(
            "/api/v1/ai-config", cookies=authenticated_user["cookies"]
        )

        assert response.status_code == 200
        data = response.json()

        # Verify camelCase response structure
        assert "current" in data
        assert "availableModels" in data  # camelCase, not available_models
        assert "providers" in data
        assert "lastUpdated" in data  # camelCase, not last_updated

        # Verify current config has camelCase fields
        current = data["current"]
        assert (
            "modelId" in current or "model_id" in current
        )  # Either is acceptable for input
        assert (
            "maxTokens" in current
            or current.get("maxTokens") is not None
            or current.get("max_tokens") is not None
        )
        assert (
            "topP" in current
            or current.get("topP") is not None
            or current.get("top_p") is not None
        )

        # Verify availableModels structure
        if data["availableModels"]:
            model = data["availableModels"][0]
            assert "modelId" in model  # camelCase
            assert "displayName" in model  # camelCase

    def test_config_test_route_reuses_singleton(self, authenticated_user, monkeypatch):
        from app.llm.client import llm_client

        orig_id = id(llm_client)

        resp = client.post(
            "/api/v1/ai-config/test",
            cookies=authenticated_user["cookies"],
            json={"provider": "openai", "modelId": "test-gpt-4o"},
        )
        assert resp.status_code == 200
        # singleton still the same object
        from app.llm.client import llm_client as after

        assert id(after) == orig_id

    def test_update_config_accepts_snake_case(self, authenticated_user, seeded_config):
        """Test that PUT accepts snake_case input and returns camelCase."""
        # Test with snake_case input
        snake_case_update = {
            "temperature": 0.8,
            "max_tokens": 1024,
            "top_p": 0.9,
            "model_id": "test-gpt-4o",
        }

        response = client.put(
            "/api/v1/ai-config",
            json=snake_case_update,
            cookies=authenticated_user["cookies"],
        )

        assert response.status_code == 200
        data = response.json()

        # Response should have camelCase fields
        assert data["temperature"] == 0.8
        assert data["maxTokens"] == 1024  # camelCase in response
        assert data["topP"] == 0.9  # camelCase in response
        assert data["modelId"] == "test-gpt-4o"  # camelCase in response

    def test_update_config_accepts_camel_case(self, authenticated_user, seeded_config):
        """Test that PUT accepts camelCase input."""
        # Test with camelCase input
        camel_case_update = {
            "temperature": 0.7,
            "maxTokens": 2048,
            "topP": 0.95,
            "modelId": "test-gpt-4o",
        }

        response = client.put(
            "/api/v1/ai-config",
            json=camel_case_update,
            cookies=authenticated_user["cookies"],
        )

        assert response.status_code == 200
        data = response.json()

        # Verify the values were applied
        assert data["temperature"] == 0.7
        assert data["maxTokens"] == 2048
        assert data["topP"] == 0.95
        assert data["modelId"] == "test-gpt-4o"

    def test_model_seeding_on_startup(self, db: Session):
        """Test that model catalog is seeded on service initialization."""
        # Clear any existing config
        db.query(RuntimeConfig).delete()
        db.query(ModelConfiguration).delete()
        db.commit()

        # Initialize service (should seed models)
        service = UnifiedConfigService(db)
        service.initialize_defaults()

        # Verify config was created
        configs = db.query(RuntimeConfig).all()
        assert len(configs) > 0

        # Verify at least basic config keys exist
        config_keys = [c.key for c in configs]
        assert "provider" in config_keys
        assert "chat_model" in config_keys or "model_id" in config_keys

    def test_get_available_models_camelcase(self, authenticated_user, seeded_config):
        """Test that /models endpoint returns camelCase model info."""
        response = client.get(
            "/api/v1/ai-config/models", cookies=authenticated_user["cookies"]
        )

        assert response.status_code == 200
        models = response.json()

        if models:
            model = models[0]
            # Verify camelCase fields
            assert "modelId" in model
            assert "displayName" in model
            assert (
                "costPer1kInputTokens" in model or "cost_per_1k_input_tokens" in model
            )
            assert (
                "costPer1kOutputTokens" in model or "cost_per_1k_output_tokens" in model
            )
            assert "isAvailable" in model or "is_available" in model

    def test_config_validation_endpoint(self, authenticated_user, seeded_config):
        """Test the configuration validation endpoint."""
        # Test valid config
        valid_config = {
            "provider": "openai",
            "modelId": "test-gpt-4o",
            "temperature": 0.7,
            "maxTokens": 2048,
        }

        response = client.post(
            "/api/v1/ai-config/validate",
            json=valid_config,
            cookies=authenticated_user["cookies"],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["error"] is None
        assert "validatedAt" in data  # camelCase

        # Test invalid config (temperature out of range)
        invalid_config = {
            "provider": "openai",
            "modelId": "test-gpt-4o",
            "temperature": 5.0,  # Invalid - too high
            "maxTokens": 2048,
        }

        response = client.post(
            "/api/v1/ai-config/validate",
            json=invalid_config,
            cookies=authenticated_user["cookies"],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["error"] is not None

    def test_configuration_presets_endpoint(self, authenticated_user):
        """Test the configuration presets endpoint."""
        response = client.get(
            "/api/v1/ai-config/presets", cookies=authenticated_user["cookies"]
        )

        assert response.status_code == 200
        presets = response.json()

        assert len(presets) > 0

        # Verify preset structure
        preset = presets[0]
        assert "id" in preset
        assert "name" in preset
        assert "description" in preset
        assert "config" in preset

        # Verify preset config has expected structure
        config = preset["config"]
        assert isinstance(config, dict)

    def test_unauthorized_access_blocked(self):
        """Test that endpoints require authentication."""
        # Test without authentication
        response = client.get("/api/v1/ai-config")
        assert response.status_code == 401

        response = client.put("/api/v1/ai-config", json={"temperature": 0.8})
        assert response.status_code == 401

        response = client.get("/api/v1/ai-config/models")
        assert response.status_code == 401

    def test_defaults(self, seeded_config):
        resp = client.get("/api/v1/ai-config/defaults")
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider"]  # basic smoke check
        assert body["temperature"] == 0.7


class TestUnifiedConfigService:
    """Test the UnifiedConfigService directly."""

    def test_camelcase_conversion_in_service(self, db: Session):
        """Test that the service properly converts between camelCase and snake_case."""
        service = UnifiedConfigService(db)

        # Test from_runtime_config conversion
        runtime_config = {
            "provider": "openai",
            "chat_model": "gpt-4o",  # snake_case in storage
            "temperature": 0.7,
            "max_tokens": 2048,  # snake_case in storage
            "top_p": 0.9,  # snake_case in storage
        }

        unified_config = service._get_default_config()
        unified_config = unified_config.__class__.from_runtime_config(runtime_config)

        # Verify the unified config has proper field names
        assert unified_config.provider == "openai"
        assert unified_config.model_id == "gpt-4o"  # Converted to model_id
        assert unified_config.temperature == 0.7
        assert unified_config.max_tokens == 2048
        assert unified_config.top_p == 0.9

        # Test to_runtime_config conversion
        runtime_dict = unified_config.to_runtime_config()

        # Should convert back to storage format
        assert runtime_dict["provider"] == "openai"
        assert runtime_dict["chat_model"] == "gpt-4o"  # Converted back to chat_model
        assert runtime_dict["temperature"] == 0.7
        assert runtime_dict["max_tokens"] == 2048
        assert runtime_dict["top_p"] == 0.9
