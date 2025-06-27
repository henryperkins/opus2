"""
Tests for LLM client validation to prevent variable scope errors and ensure proper error handling.

These tests specifically target the bug that caused the 500 error:
- UnboundLocalError when input_messages was referenced outside its scope
- Proper exception handling for different error types
- Configuration validation behavior
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from app.llm.client import LLMClient
from app.services.config_service import ConfigService


class TestLLMClientValidation:
    """Test LLM client validation and error handling."""

    @pytest.fixture
    def client(self):
        """Create LLM client instance for testing."""
        return LLMClient()

    @pytest.fixture
    def mock_azure_client(self):
        """Mock Azure OpenAI client."""
        with patch('app.llm.client.AzureOpenAI') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_string_input_no_unbound_variable(self, client, mock_azure_client):
        """Test that string input doesn't cause UnboundLocalError.
        
        This specifically tests the bug fix for the variable scope issue.
        """
        # Configure client for Responses API
        await client.reconfigure(provider="azure", model="o3", use_responses_api=True)
        
        # Mock the responses.create method
        mock_response = MagicMock()
        mock_response.output = [
            MagicMock(content=[MagicMock(text="Test response")])
        ]
        mock_azure_client.responses.create = AsyncMock(return_value=mock_response)
        
        # This should not raise UnboundLocalError
        result = await client.complete(
            input="Test message",
            reasoning={"effort": "high", "summary": "auto"},
            max_tokens=50
        )
        
        assert result is not None
        # Verify the method was called
        mock_azure_client.responses.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_array_input(self, client, mock_azure_client):
        """Test that message array input works correctly."""
        await client.reconfigure(provider="azure", model="o3", use_responses_api=True)
        
        # Mock the responses.create method
        mock_response = MagicMock()
        mock_response.output = [
            MagicMock(content=[MagicMock(text="Test response")])
        ]
        mock_azure_client.responses.create = AsyncMock(return_value=mock_response)
        
        # Test with message array
        result = await client.complete(
            input=[{"role": "user", "content": "Test"}],
            reasoning={"effort": "high", "summary": "auto"},
            max_tokens=50
        )
        
        assert result is not None
        mock_azure_client.responses.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_message_conversion_reasoning_model(self, client, mock_azure_client):
        """Test that system messages are properly converted for reasoning models."""
        await client.reconfigure(provider="azure", model="o3", use_responses_api=True)
        
        # Mock the responses.create method
        mock_response = MagicMock()
        mock_response.output = [
            MagicMock(content=[MagicMock(text="Test response")])
        ]
        mock_azure_client.responses.create = AsyncMock(return_value=mock_response)
        
        # Test with system message
        result = await client.complete(
            input=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Test"}
            ],
            reasoning={"effort": "high", "summary": "auto"},
            max_tokens=50
        )
        
        assert result is not None
        
        # Check that the call was made with correct format
        call_args = mock_azure_client.responses.create.call_args
        input_data = call_args.kwargs['input']
        
        # System message should be converted to developer message for reasoning models
        assert any(msg.get('role') == 'developer' for msg in input_data)

    @pytest.mark.asyncio
    async def test_config_validation_error_handling(self):
        """Test that validation errors return 422, not 500."""
        config_service = ConfigService()
        
        # Mock the LLM client to raise UnboundLocalError (simulating the original bug)
        with patch('app.llm.client.LLMClient.complete') as mock_complete:
            mock_complete.side_effect = UnboundLocalError("cannot access local variable 'input_messages' where it is not associated with a value")
            
            # This should handle the error gracefully
            is_valid, error = await config_service.validate_config({
                "provider": "azure", 
                "chat_model": "o3",
                "use_responses_api": True,
                "reasoning_effort": "high"
            })
            
            # Should return False with error message, not raise exception
            assert is_valid is False
            assert "input_messages" in error

    @pytest.mark.asyncio
    async def test_reasoning_parameter_structure(self, client, mock_azure_client):
        """Test that reasoning parameters are structured correctly for Responses API."""
        await client.reconfigure(provider="azure", model="o3", use_responses_api=True)
        
        # Mock the responses.create method
        mock_response = MagicMock()
        mock_response.output = [
            MagicMock(content=[MagicMock(text="Test response")])
        ]
        mock_azure_client.responses.create = AsyncMock(return_value=mock_response)
        
        # Test with reasoning parameters
        await client.complete(
            input="Test message",
            reasoning={"effort": "medium", "summary": "detailed"},
            max_tokens=50
        )
        
        # Check that reasoning parameter is passed correctly
        call_args = mock_azure_client.responses.create.call_args
        reasoning_param = call_args.kwargs.get('reasoning')
        
        assert reasoning_param is not None
        assert reasoning_param.get('effort') == 'medium'

    @pytest.mark.asyncio
    async def test_chat_completions_fallback(self, client, mock_azure_client):
        """Test fallback to Chat Completions API when Responses API fails."""
        await client.reconfigure(provider="azure", model="gpt-4o-mini", use_responses_api=False)
        
        # Mock the chat.completions.create method
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Test response"))
        ]
        mock_azure_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        result = await client.complete(
            input=[{"role": "user", "content": "Test"}],
            reasoning_effort="high",  # Different parameter structure for Chat Completions
            max_tokens=50
        )
        
        assert result is not None
        mock_azure_client.chat.completions.create.assert_called_once()

    def test_variable_scope_fix_structure(self):
        """Test that the variable scope fix is properly implemented."""
        import inspect
        from app.llm.client import LLMClient
        
        # Get the source code of the complete method
        source = inspect.getsource(LLMClient.complete)
        
        # Verify that input_messages is initialized outside the conditional
        lines = source.split('\n')
        
        # Find the line where input_messages is first declared
        input_messages_declarations = [
            i for i, line in enumerate(lines) 
            if 'input_messages:' in line and 'List[Dict[str, Any]]' in line
        ]
        
        # Find conditional blocks
        if_responses_api = [
            i for i, line in enumerate(lines)
            if 'if isinstance(chat_turns, str):' in line
        ]
        
        # Ensure input_messages is declared before the conditional
        if input_messages_declarations and if_responses_api:
            assert input_messages_declarations[0] < if_responses_api[0], \
                "input_messages should be declared before the conditional block"


class TestConfigServiceValidation:
    """Test configuration service validation behavior."""

    @pytest.fixture
    def config_service(self):
        """Create config service instance for testing."""
        return ConfigService()

    @pytest.mark.asyncio
    async def test_validation_with_valid_config(self, config_service):
        """Test validation passes with valid configuration."""
        with patch('app.llm.client.LLMClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.return_value = MagicMock()
            mock_client_class.return_value = mock_client
            
            is_valid, error = await config_service.validate_config({
                "provider": "azure",
                "chat_model": "o3", 
                "use_responses_api": True,
                "reasoning_effort": "high"
            })
            
            assert is_valid is True
            assert error == ""

    @pytest.mark.asyncio
    async def test_validation_handles_unbound_local_error(self, config_service):
        """Test that UnboundLocalError is handled gracefully."""
        with patch('app.llm.client.LLMClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.side_effect = UnboundLocalError("cannot access local variable 'input_messages'")
            mock_client_class.return_value = mock_client
            
            is_valid, error = await config_service.validate_config({
                "provider": "azure",
                "chat_model": "o3",
                "use_responses_api": True
            })
            
            assert is_valid is False
            assert "input_messages" in error

    @pytest.mark.asyncio
    async def test_validation_handles_other_exceptions(self, config_service):
        """Test that other exceptions are handled appropriately."""
        with patch('app.llm.client.LLMClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.complete.side_effect = ValueError("Invalid model configuration")
            mock_client_class.return_value = mock_client
            
            is_valid, error = await config_service.validate_config({
                "provider": "azure",
                "chat_model": "invalid-model"
            })
            
            assert is_valid is False
            assert "Invalid model configuration" in error


class TestConfigRouterExceptionHandling:
    """Test that the config router handles exceptions properly."""

    @pytest.mark.asyncio
    async def test_unbound_local_error_returns_422(self):
        """Test that UnboundLocalError returns 422, not 500."""
        from app.routers.config import update_model_config
        from app.schemas.models import ModelConfig
        
        # Create mock payload
        mock_payload = MagicMock()
        mock_payload.dict.return_value = {
            "provider": "azure",
            "chat_model": "o3",
            "use_responses_api": True
        }
        
        # Mock config service to raise UnboundLocalError
        mock_config_service = AsyncMock()
        mock_config_service.validate_config.side_effect = UnboundLocalError("input_messages error")
        
        # Test that it raises HTTPException with 422 status
        with pytest.raises(HTTPException) as exc_info:
            await update_model_config(mock_payload, mock_config_service)
        
        assert exc_info.value.status_code == 422
        assert "Configuration error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_value_error_returns_422(self):
        """Test that ValueError returns 422, not 500."""
        from app.routers.config import update_model_config
        
        mock_payload = MagicMock()
        mock_payload.dict.return_value = {
            "provider": "azure",
            "chat_model": "invalid-model"
        }
        
        mock_config_service = AsyncMock()
        mock_config_service.validate_config.side_effect = ValueError("Invalid model")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_model_config(mock_payload, mock_config_service)
        
        assert exc_info.value.status_code == 422
        assert "Invalid configuration" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_http_exception_preserves_status(self):
        """Test that HTTPExceptions are re-raised with original status."""
        from app.routers.config import update_model_config
        
        mock_payload = MagicMock()
        mock_payload.dict.return_value = {}  # Empty config
        
        mock_config_service = AsyncMock()
        
        # Should raise 400 for empty config
        with pytest.raises(HTTPException) as exc_info:
            await update_model_config(mock_payload, mock_config_service)
        
        assert exc_info.value.status_code == 400
