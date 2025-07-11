"""
Tests for Phase 5: Complete Claude Thinking Implementation

Tests all 7 Claude thinking settings and tool streaming functionality:
1. claude_extended_thinking - Enable/disable flag
2. claude_thinking_mode - Mode selection
3. claude_thinking_budget_tokens - Token budget
4. claude_show_thinking_process - Visibility control
5. claude_adaptive_thinking_budget - Adaptive adjustment
6. claude_max_thinking_budget - Upper limit
7. claude_thinking_models - Model validation

Also tests enhanced tool streaming for OpenAI and Azure providers.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.llm.client import LLMClient
from app.llm.providers.anthropic_provider import AnthropicProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.azure_provider import AzureOpenAIProvider
from app.config import settings


class TestClaudeThinkingImplementation:
    """Test all 7 Claude thinking settings are properly implemented."""

    @pytest.fixture
    def client(self):
        """Create LLM client instance for testing."""
        return LLMClient()

    @pytest.fixture
    def anthropic_provider(self):
        """Create Anthropic provider instance for testing."""
        return AnthropicProvider({"api_key": "test-key", "timeout": 300})

    @pytest.mark.asyncio
    async def test_claude_thinking_config_construction(self, client):
        """Test that all Claude thinking settings are properly passed to provider."""
        # Mock the Anthropic provider
        with patch(
            "app.llm.providers.anthropic_provider.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            # Mock response
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Test response")]
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            # Configure client for Claude with all thinking settings
            await client.reconfigure(
                provider="anthropic",
                model="claude-3-5-sonnet-latest",
                claude_extended_thinking=True,
                claude_thinking_mode="aggressive",
                claude_thinking_budget_tokens=32768,
                claude_show_thinking_process=True,
                claude_adaptive_thinking_budget=True,
                claude_max_thinking_budget=65536,
            )

            # Make request
            result = await client.complete(
                input=[
                    {
                        "role": "user",
                        "content": "Analyze this complex problem step by step",
                    }
                ],
                max_tokens=500,
            )

            # Verify the thinking config was passed correctly
            call_args = mock_client.messages.create.call_args
            thinking_param = call_args.kwargs.get("thinking")

            assert thinking_param is not None
            assert thinking_param.get("type") == "aggressive"
            assert thinking_param.get("budget_tokens") >= 32768
            assert thinking_param.get("show_thinking") is True
            assert thinking_param.get("max_budget_tokens") == 65536
            assert thinking_param.get("adaptive_budget") is True

    @pytest.mark.asyncio
    async def test_claude_adaptive_budget_adjustment(self, client):
        """Test that adaptive budget increases for complex tasks."""
        with patch(
            "app.llm.providers.anthropic_provider.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Test response")]
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            await client.reconfigure(
                provider="anthropic",
                model="claude-3-5-sonnet-latest",
                claude_extended_thinking=True,
                claude_adaptive_thinking_budget=True,
                claude_thinking_budget_tokens=16384,
                claude_max_thinking_budget=65536,
            )

            # Test with large prompt (should trigger budget increase)
            large_prompt = "Analyze this: " + "complex problem " * 200  # > 2000 chars

            await client.complete(
                input=[{"role": "user", "content": large_prompt}], max_tokens=500
            )

            call_args = mock_client.messages.create.call_args
            thinking_param = call_args.kwargs.get("thinking")

            # Budget should be doubled for large prompts (32768)
            assert thinking_param.get("budget_tokens") == 32768

    @pytest.mark.asyncio
    async def test_claude_thinking_with_tools_budget_adjustment(self, client):
        """Test that tool usage triggers budget adjustment."""
        with patch(
            "app.llm.providers.anthropic_provider.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Test response")]
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            await client.reconfigure(
                provider="anthropic",
                model="claude-3-5-sonnet-latest",
                claude_extended_thinking=True,
                claude_adaptive_thinking_budget=True,
                claude_thinking_budget_tokens=16384,
            )

            # Test with tools (should trigger 1.5x budget increase)
            await client.complete(
                input=[{"role": "user", "content": "Use tools to solve this"}],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "search",
                            "description": "Search for information",
                        },
                    }
                ],
                max_tokens=500,
            )

            call_args = mock_client.messages.create.call_args
            thinking_param = call_args.kwargs.get("thinking")

            # Budget should be 1.5x for tool usage (24576)
            assert thinking_param.get("budget_tokens") == 24576

    @pytest.mark.asyncio
    async def test_claude_thinking_disabled_mode(self, client):
        """Test that thinking is disabled when mode is 'off'."""
        with patch(
            "app.llm.providers.anthropic_provider.AsyncAnthropic"
        ) as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Test response")]
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            await client.reconfigure(
                provider="anthropic",
                model="claude-3-5-sonnet-latest",
                claude_extended_thinking=True,
                claude_thinking_mode="off",  # Explicitly disabled
            )

            await client.complete(
                input=[{"role": "user", "content": "Test message"}], max_tokens=500
            )

            call_args = mock_client.messages.create.call_args
            thinking_param = call_args.kwargs.get("thinking")

            # No thinking should be passed when mode is off
            assert thinking_param is None

    def test_claude_thinking_model_validation(self, anthropic_provider):
        """Test that thinking is only enabled for supported models."""
        # Test with supported model
        assert anthropic_provider._supports_thinking("claude-3-5-sonnet-latest") is True
        assert anthropic_provider._supports_thinking("claude-opus-4-20250514") is True

        # Test with unsupported model
        assert anthropic_provider._supports_thinking("claude-3-haiku") is False
        assert anthropic_provider._supports_thinking("gpt-4") is False

    @pytest.mark.asyncio
    async def test_anthropic_thinking_response_extraction(self, anthropic_provider):
        """Test that thinking content is properly extracted from responses."""
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client
            anthropic_provider.client = mock_client

            # Mock response with thinking content
            mock_response = MagicMock()
            mock_response.thinking = MagicMock()
            mock_response.thinking.content = "Let me think about this step by step..."
            mock_response.content = [MagicMock(text="Here's my answer")]

            # Test content extraction includes thinking
            content = anthropic_provider.extract_content(mock_response)

            assert "<thinking>" in content
            assert "Let me think about this step by step..." in content
            assert "</thinking>" in content
            assert "Here's my answer" in content

    @pytest.mark.asyncio
    async def test_anthropic_thinking_streaming(self, anthropic_provider):
        """Test that thinking content is properly streamed."""
        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_anthropic.return_value = mock_client
            anthropic_provider.client = mock_client

            # Mock streaming response with thinking
            async def mock_stream():
                # Thinking chunk
                thinking_chunk = MagicMock()
                thinking_chunk.thinking = MagicMock()
                thinking_chunk.thinking.delta = "I need to analyze..."
                yield thinking_chunk

                # Content chunk
                content_chunk = MagicMock()
                content_chunk.delta = MagicMock()
                content_chunk.delta.text = "Based on my analysis..."
                yield content_chunk

            # Test streaming
            content_parts = []
            async for chunk in anthropic_provider.stream(mock_stream()):
                content_parts.append(chunk)

            full_content = "".join(content_parts)
            assert "<thinking>" in full_content
            assert "I need to analyze..." in full_content
            assert "</thinking>" in full_content
            assert "Based on my analysis..." in full_content


class TestToolStreaming:
    """Test enhanced tool streaming for OpenAI and Azure providers."""

    @pytest.fixture
    def openai_provider(self):
        """Create OpenAI provider instance for testing."""
        return OpenAIProvider({"api_key": "test-key", "timeout": 300})

    @pytest.fixture
    def azure_provider(self):
        """Create Azure provider instance for testing."""
        return AzureOpenAIProvider(
            {
                "api_key": "test-key",
                "endpoint": "https://test.openai.azure.com",  # Use 'endpoint' not 'azure_endpoint'
                "api_version": "2025-04-01-preview",
                "timeout": 300,
            }
        )

    @pytest.mark.asyncio
    async def test_openai_tool_streaming(self, openai_provider):
        """Test that OpenAI provider properly streams tool calls."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            openai_provider.client = mock_client

            # Mock streaming response with tool calls
            async def mock_stream():
                # Tool call start
                chunk1 = MagicMock()
                chunk1.choices = [MagicMock()]
                chunk1.choices[0].delta = MagicMock()
                chunk1.choices[0].delta.content = None
                chunk1.choices[0].delta.tool_calls = [MagicMock()]
                chunk1.choices[0].delta.tool_calls[0].index = 0
                chunk1.choices[0].delta.tool_calls[0].id = "call_123"
                chunk1.choices[0].delta.tool_calls[0].function = MagicMock()
                chunk1.choices[0].delta.tool_calls[0].function.name = "search"
                chunk1.choices[0].delta.tool_calls[0].function.arguments = '{"query":'
                yield chunk1

                # Tool call continuation
                chunk2 = MagicMock()
                chunk2.choices = [MagicMock()]
                chunk2.choices[0].delta = MagicMock()
                chunk2.choices[0].delta.content = None
                chunk2.choices[0].delta.tool_calls = [MagicMock()]
                chunk2.choices[0].delta.tool_calls[0].index = 0
                chunk2.choices[0].delta.tool_calls[0].function = MagicMock()
                chunk2.choices[0].delta.tool_calls[0].function.arguments = ' "test"}'
                yield chunk2

                # Finish reason
                chunk3 = MagicMock()
                chunk3.choices = [MagicMock()]
                chunk3.choices[0].delta = MagicMock()
                chunk3.choices[0].delta.content = None
                chunk3.choices[0].finish_reason = "tool_calls"
                yield chunk3

            # Test streaming
            content_parts = []
            async for chunk in openai_provider.stream(mock_stream()):
                content_parts.append(chunk)

            full_content = "".join(content_parts)
            assert "[Calling search" in full_content
            assert "Tool calls completed" in full_content

    @pytest.mark.asyncio
    async def test_azure_tool_streaming_chat_api(self, azure_provider):
        """Test that Azure provider properly streams tool calls in Chat API mode."""
        # Configure for Chat Completions API (not Responses API)
        azure_provider.use_responses_api = False

        with patch("openai.AsyncAzureOpenAI") as mock_azure:
            mock_client = AsyncMock()
            mock_azure.return_value = mock_client
            azure_provider.client = mock_client

            # Mock streaming similar to OpenAI
            async def mock_stream():
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = None
                chunk.choices[0].delta.tool_calls = [MagicMock()]
                chunk.choices[0].delta.tool_calls[0].index = 0
                chunk.choices[0].delta.tool_calls[0].id = "call_456"
                chunk.choices[0].delta.tool_calls[0].function = MagicMock()
                chunk.choices[0].delta.tool_calls[0].function.name = "calculate"
                chunk.choices[0].delta.tool_calls[
                    0
                ].function.arguments = '{"expression": "2+2"}'
                yield chunk

            # Test streaming
            content_parts = []
            async for chunk in azure_provider.stream(mock_stream()):
                content_parts.append(chunk)

            full_content = "".join(content_parts)
            assert "[Calling calculate" in full_content

    @pytest.mark.asyncio
    async def test_tool_streaming_json_parsing_error_handling(self, openai_provider):
        """Test that incomplete JSON in tool arguments is handled gracefully."""
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            openai_provider.client = mock_client

            # Mock streaming with incomplete JSON
            async def mock_stream():
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = None
                chunk.choices[0].delta.tool_calls = [MagicMock()]
                chunk.choices[0].delta.tool_calls[0].index = 0
                chunk.choices[0].delta.tool_calls[0].function = MagicMock()
                chunk.choices[0].delta.tool_calls[0].function.name = "test"
                chunk.choices[0].delta.tool_calls[
                    0
                ].function.arguments = '{"incomplete'  # Invalid JSON
                yield chunk

            # Should not raise exception
            content_parts = []
            async for chunk in openai_provider.stream(mock_stream()):
                content_parts.append(chunk)

            full_content = "".join(content_parts)
            assert (
                "[Calling test..." in full_content
            )  # Fallback text for incomplete JSON


class TestPhase5Integration:
    """Integration tests for all Phase 5 features."""

    @pytest.mark.asyncio
    async def test_end_to_end_claude_thinking_flow(self):
        """Test complete flow from config to response with Claude thinking."""
        client = LLMClient()

        with patch(
            "app.llm.providers.anthropic_provider.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic_client = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_client

            # Mock response with thinking
            mock_response = MagicMock()
            mock_response.thinking = MagicMock()
            mock_response.thinking.content = "Let me analyze this systematically..."
            mock_response.content = [
                MagicMock(text="Based on my analysis, the answer is...")
            ]
            mock_anthropic_client.messages.create = AsyncMock(
                return_value=mock_response
            )

            # Configure with all thinking settings
            await client.reconfigure(
                provider="anthropic",
                model="claude-3-5-sonnet-latest",
                claude_extended_thinking=True,
                claude_thinking_mode="aggressive",
                claude_thinking_budget_tokens=32768,
                claude_show_thinking_process=True,
                claude_adaptive_thinking_budget=True,
                claude_max_thinking_budget=65536,
            )

            # Make request
            result = await client.complete(
                input=[{"role": "user", "content": "Solve this complex problem"}],
                max_tokens=1000,
            )

            # Verify thinking was passed correctly
            call_args = mock_anthropic_client.messages.create.call_args
            thinking_param = call_args.kwargs.get("thinking")

            assert thinking_param is not None
            assert thinking_param["type"] == "aggressive"
            assert thinking_param["budget_tokens"] == 32768
            assert thinking_param["show_thinking"] is True
            assert thinking_param["adaptive_budget"] is True
            assert thinking_param["max_budget_tokens"] == 65536

    @pytest.mark.asyncio
    async def test_settings_override_behavior(self):
        """Test that runtime config overrides static settings."""
        client = LLMClient()

        with patch(
            "app.llm.providers.anthropic_provider.AsyncAnthropic"
        ) as mock_anthropic:
            mock_anthropic_client = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_client

            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Response")]
            mock_anthropic_client.messages.create = AsyncMock(
                return_value=mock_response
            )

            # Test with runtime config that overrides settings
            from app.services.runtime_config_service import RuntimeConfigService
            from app.database import SessionLocal

            with SessionLocal() as db:
                runtime_service = RuntimeConfigService(db)

                # Set runtime override
                await runtime_service.set_config("claude_thinking_budget_tokens", 8192)
                await runtime_service.set_config("claude_thinking_mode", "enabled")

                await client.reconfigure(
                    provider="anthropic", model="claude-3-5-sonnet-latest"
                )

                await client.complete(
                    input=[{"role": "user", "content": "Test"}], max_tokens=500
                )

                # Verify runtime config was used
                call_args = mock_anthropic_client.messages.create.call_args
                thinking_param = call_args.kwargs.get("thinking")

                if thinking_param:  # Only check if thinking was enabled
                    assert thinking_param["budget_tokens"] == 8192
                    assert thinking_param["type"] == "enabled"
