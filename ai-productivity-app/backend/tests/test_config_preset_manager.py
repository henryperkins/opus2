"""
Test suite for ConfigPresetManager dynamic adaptation functionality
"""

import pytest
from unittest.mock import Mock, MagicMock
from app.services.config_preset_manager import ConfigPresetManager
from app.schemas.generation import UnifiedModelConfig


class TestConfigPresetManager:
    """Test cases for dynamic preset adaptation"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock()
    
    @pytest.fixture
    def mock_model_service(self):
        """Create a mock model service"""
        service = Mock()
        
        # Mock model availability checks
        def get_model_info(model_id):
            model_map = {
                # OpenAI models
                "gpt-4o": Mock(provider="openai", is_available=True),
                "gpt-4o-mini": Mock(provider="openai", is_available=True),
                
                # Azure models
                "o3": Mock(provider="azure", is_available=True),
                "o4-mini": Mock(provider="azure", is_available=True),
                "gpt-4.1": Mock(provider="azure", is_available=True),
                
                # Anthropic models
                "claude-opus-4-20250514": Mock(provider="anthropic", is_available=True),
                "claude-sonnet-4-20250522": Mock(provider="anthropic", is_available=True),
                "claude-3-5-haiku-20241022": Mock(provider="anthropic", is_available=True),
                "claude-3-5-sonnet-20241022": Mock(provider="anthropic", is_available=True),
            }
            return model_map.get(model_id)
        
        service.get_model_info = Mock(side_effect=get_model_info)
        return service
    
    @pytest.fixture
    def preset_manager(self, mock_db, mock_model_service):
        """Create a preset manager with mocked dependencies"""
        manager = ConfigPresetManager(mock_db)
        manager.model_service = mock_model_service
        return manager
    
    def test_get_presets_returns_all_presets(self, preset_manager):
        """Test that all presets are returned with proper formatting"""
        presets = preset_manager.get_presets()
        
        assert len(presets) == 5  # balanced, creative, fast, powerful, coding
        
        # Check preset structure
        for preset in presets:
            assert "id" in preset
            assert "name" in preset
            assert "description" in preset
            assert "(adapts to your provider)" in preset["description"]
            assert "provider_configs" in preset
    
    def test_apply_preset_direct_match(self, preset_manager):
        """Test applying a preset when provider has direct configuration"""
        current_config = UnifiedModelConfig(
            provider="azure",
            model_id="gpt-4o",
            temperature=0.7,
            max_tokens=2048
        )
        
        # Apply balanced preset
        result = preset_manager.apply_preset("balanced", current_config)
        
        assert result["provider"] == "azure"
        assert result["model_id"] == "gpt-4.1"
        assert result["use_responses_api"] is True
        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 2048
    
    def test_apply_preset_with_adaptation(self, preset_manager):
        """Test preset adaptation when switching providers"""
        current_config = UnifiedModelConfig(
            provider="anthropic",
            model_id="claude-3-opus-20240229",
            temperature=0.7,
            max_tokens=2048
        )
        
        # Apply powerful preset
        result = preset_manager.apply_preset("powerful", current_config)
        
        assert result["provider"] == "anthropic"
        assert result["model_id"] == "claude-opus-4-20250514"
        assert result["claude_extended_thinking"] is True
        assert result["claude_thinking_mode"] == "aggressive"
        assert result["max_tokens"] == 32000  # Adjusted for Opus 4
        
        # Should not have Azure-specific fields
        assert "use_responses_api" not in result
        assert "enable_reasoning" not in result
    
    def test_azure_reasoning_model_adjustments(self, preset_manager):
        """Test that Azure reasoning models get proper parameter adjustments"""
        current_config = UnifiedModelConfig(
            provider="azure",
            model_id="gpt-4o",
            temperature=0.7
        )
        
        # Apply powerful preset (which uses o3 for Azure)
        result = preset_manager.apply_preset("powerful", current_config)
        
        assert result["model_id"] == "o3"
        assert result["temperature"] == 1.0  # Required for reasoning models
        assert result["enable_reasoning"] is True
        assert result["reasoning_effort"] == "high"
        assert result["use_responses_api"] is True
    
    def test_model_tier_equivalence(self, preset_manager):
        """Test model equivalence mapping across providers"""
        # Test small tier
        assert preset_manager._get_model_tier("gpt-4o-mini") == "small"
        assert preset_manager._get_model_tier("o4-mini") == "small"
        assert preset_manager._get_model_tier("claude-3-5-haiku-20241022") == "small"
        
        # Test medium tier
        assert preset_manager._get_model_tier("gpt-4.1") == "medium"
        assert preset_manager._get_model_tier("claude-3-5-sonnet-20241022") == "medium"
        
        # Test large tier
        assert preset_manager._get_model_tier("gpt-4o") == "large"
        assert preset_manager._get_model_tier("o3") == "large"
        assert preset_manager._get_model_tier("claude-opus-4-20250514") == "large"
    
    def test_find_equivalent_model(self, preset_manager):
        """Test finding equivalent models across providers"""
        # Small model equivalents
        equiv = preset_manager._find_equivalent_model("gpt-4o-mini", "anthropic", "fast")
        assert equiv == "claude-3-5-haiku-20241022"
        
        equiv = preset_manager._find_equivalent_model("claude-3-5-haiku-20241022", "azure", "fast")
        assert equiv == "o4-mini"
        
        # Large model equivalents
        equiv = preset_manager._find_equivalent_model("gpt-4o", "anthropic", "powerful")
        assert equiv == "claude-opus-4-20250514"
        
        equiv = preset_manager._find_equivalent_model("claude-opus-4-20250514", "azure", "powerful")
        assert equiv == "o3"
    
    def test_clean_provider_specific_fields(self, preset_manager):
        """Test removal of provider-specific fields when switching"""
        # Azure to Anthropic
        config = {
            "model_id": "claude-3-5-sonnet",
            "temperature": 0.7,
            "use_responses_api": True,
            "enable_reasoning": True,
            "reasoning_effort": "medium"
        }
        
        cleaned = preset_manager._clean_provider_specific_fields(config, "anthropic")
        
        assert "use_responses_api" not in cleaned
        assert "enable_reasoning" not in cleaned
        assert "reasoning_effort" not in cleaned
        assert cleaned["model_id"] == "claude-3-5-sonnet"
        assert cleaned["temperature"] == 0.7
        
        # Anthropic to OpenAI
        config = {
            "model_id": "gpt-4o",
            "temperature": 0.7,
            "claude_extended_thinking": True,
            "claude_thinking_mode": "enabled"
        }
        
        cleaned = preset_manager._clean_provider_specific_fields(config, "openai")
        
        assert "claude_extended_thinking" not in cleaned
        assert "claude_thinking_mode" not in cleaned
        assert cleaned["model_id"] == "gpt-4o"
        assert cleaned["temperature"] == 0.7
    
    def test_preset_not_found(self, preset_manager):
        """Test error handling for non-existent preset"""
        current_config = UnifiedModelConfig(provider="openai", model_id="gpt-4o")
        
        with pytest.raises(ValueError, match="Preset 'nonexistent' not found"):
            preset_manager.apply_preset("nonexistent", current_config)
    
    def test_model_not_available_fallback(self, preset_manager):
        """Test fallback when model is not available"""
        # Mock a model as unavailable
        preset_manager.model_service.get_model_info.return_value = None
        
        current_config = UnifiedModelConfig(
            provider="azure",
            model_id="gpt-4o"
        )
        
        # Apply preset that would normally use an unavailable model
        result = preset_manager.apply_preset("balanced", current_config)
        
        # Should fall back to default model
        assert result["model_id"] == "gpt-4.1"  # Default for Azure
    
    def test_coding_preset_parameters(self, preset_manager):
        """Test coding preset applies appropriate parameters"""
        current_config = UnifiedModelConfig(provider="anthropic", model_id="claude-3-opus")
        
        result = preset_manager.apply_preset("coding", current_config)
        
        assert result["temperature"] == 0.2  # Low temp for deterministic output
        assert result["model_id"] == "claude-opus-4-20250514"
        assert result["claude_extended_thinking"] is True
        assert result["max_tokens"] == 32000
    
    def test_creative_preset_parameters(self, preset_manager):
        """Test creative preset applies appropriate parameters"""
        current_config = UnifiedModelConfig(provider="openai", model_id="gpt-4")
        
        result = preset_manager.apply_preset("creative", current_config)
        
        assert result["temperature"] == 1.2  # Higher temp for creativity
        assert result["frequency_penalty"] == 0.2
        assert result["presence_penalty"] == 0.2
        assert result["model_id"] == "gpt-4o"
        assert result["max_tokens"] == 3000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])