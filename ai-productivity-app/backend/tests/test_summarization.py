"""Tests for summarization service functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.summarization_service import SummarizationService


class TestSummarizationService:
    """Test summarization service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.summarizer = SummarizationService(max_summary_tokens=500)

    def test_should_summarize_chunks_by_count(self):
        """Test chunk overflow detection by count."""

        chunks = [
            {
                "content": "short content",
                "score": 0.9,
                "chunk_id": i,
                "metadata": {"file_path": f"file_{i}.py"},
            }
            for i in range(10)
        ]

        kept_chunks, overflow_chunks = self.summarizer.should_summarize_chunks(
            chunks, max_context_tokens=10000, keep_top_n=3
        )

        assert len(kept_chunks) == 3
        assert len(overflow_chunks) == 7

        # Should keep highest scoring chunks
        assert kept_chunks[0]["score"] == 0.9
        assert kept_chunks[0]["chunk_id"] == 0

    def test_should_summarize_chunks_by_tokens(self):
        """Test chunk overflow detection by token count."""

        chunks = [
            {
                "content": "This is a medium length piece of content "
                * 20,  # ~80 tokens each
                "score": 0.8 - (i * 0.1),  # Decreasing scores
                "chunk_id": i,
                "metadata": {"file_path": f"file_{i}.py"},
            }
            for i in range(5)
        ]

        # Small token limit should force summarization
        kept_chunks, overflow_chunks = self.summarizer.should_summarize_chunks(
            chunks, max_context_tokens=100, keep_top_n=5
        )

        # Should keep fewer chunks due to token limit
        assert len(kept_chunks) < 5
        assert len(overflow_chunks) > 0

        # Should prioritize by score
        assert kept_chunks[0]["score"] > kept_chunks[-1]["score"]

    def test_should_summarize_conversation_by_length(self):
        """Test conversation summarization by length."""

        conversation = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language..."},
            {"role": "user", "content": "How do I install it?"},
            {"role": "assistant", "content": "You can install Python by..."},
            {"role": "user", "content": "What about virtual environments?"},
            {"role": "assistant", "content": "Virtual environments are..."},
            {"role": "user", "content": "Current question about FastAPI"},
            {"role": "assistant", "content": "FastAPI is..."},
        ]

        kept_messages, old_messages = self.summarizer.should_summarize_conversation(
            conversation, max_conversation_tokens=200
        )

        # Should keep recent messages
        assert len(kept_messages) >= 2  # At least last exchange
        assert len(old_messages) > 0

        # Should keep the most recent messages
        assert kept_messages[-1]["content"] == "FastAPI is..."
        assert kept_messages[-2]["content"] == "Current question about FastAPI"

    def test_should_summarize_conversation_short_messages(self):
        """Test conversation handling with short message list."""

        conversation = [
            {"role": "user", "content": "Short question"},
            {"role": "assistant", "content": "Short answer"},
        ]

        kept_messages, old_messages = self.summarizer.should_summarize_conversation(
            conversation, max_conversation_tokens=1000
        )

        # Should keep all messages when conversation is short
        assert len(kept_messages) == 2
        assert len(old_messages) == 0

    @pytest.mark.asyncio
    async def test_summarize_overflow_chunks(self):
        """Test overflow chunk summarization."""

        overflow_chunks = [
            {
                "content": "def function1():\n    return 'test1'",
                "metadata": {
                    "file_path": "utils.py",
                    "symbol_name": "function1",
                    "symbol_type": "function",
                    "start_line": 1,
                    "end_line": 2,
                },
            },
            {
                "content": "class TestClass:\n    def method(self):\n        pass",
                "metadata": {
                    "file_path": "classes.py",
                    "symbol_name": "TestClass",
                    "symbol_type": "class",
                    "start_line": 10,
                    "end_line": 13,
                },
            },
        ]

        # Mock the LLM client
        with patch("app.services.summarization_service.llm_client") as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = (
                "Summary: Contains function1 and TestClass with basic implementations."
            )
            mock_client.complete = AsyncMock(return_value=mock_response)

            summary = await self.summarizer.summarize_overflow_chunks(
                overflow_chunks,
                query_context="looking for utility functions",
                focus_areas=["functions", "classes"],
            )

            assert summary.startswith("## Summary of Additional Context")
            assert "function1" in summary
            assert "TestClass" in summary

            # Verify LLM was called with appropriate prompt
            mock_client.complete.assert_called_once()
            call_args = mock_client.complete.call_args
            prompt = call_args[1]["messages"][0]["content"]

            assert "looking for utility functions" in prompt
            assert "functions, classes" in prompt
            assert "def function1()" in prompt
            assert "class TestClass" in prompt

    @pytest.mark.asyncio
    async def test_summarize_conversation_history(self):
        """Test conversation history summarization."""

        old_messages = [
            {"role": "user", "content": "How do I create a FastAPI app?"},
            {"role": "assistant", "content": "To create a FastAPI app, you need to..."},
            {"role": "user", "content": "What about database connections?"},
            {
                "role": "assistant",
                "content": "For database connections, you can use SQLAlchemy...",
            },
        ]

        # Mock the LLM client
        with patch("app.services.summarization_service.llm_client") as mock_client:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = (
                "Previous discussion covered FastAPI app creation and database setup with SQLAlchemy."
            )
            mock_client.complete = AsyncMock(return_value=mock_response)

            summary = await self.summarizer.summarize_conversation_history(old_messages)

            assert summary.startswith("## Previous Conversation Summary")
            assert "FastAPI" in summary
            assert "database" in summary

            # Verify LLM was called
            mock_client.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_with_llm_error(self):
        """Test graceful handling of LLM errors during summarization."""

        overflow_chunks = [
            {
                "content": "def test_function(): pass",
                "metadata": {"file_path": "test.py"},
            }
        ]

        # Mock LLM client to raise an exception
        with patch("app.services.summarization_service.llm_client") as mock_client:
            mock_client.complete = AsyncMock(side_effect=Exception("LLM error"))

            summary = await self.summarizer.summarize_overflow_chunks(overflow_chunks)

            # Should return a fallback summary
            assert "Additional relevant code found" in summary
            assert "test.py" in summary

    def test_empty_chunks_handling(self):
        """Test handling of empty chunk lists."""

        kept_chunks, overflow_chunks = self.summarizer.should_summarize_chunks(
            [], max_context_tokens=1000, keep_top_n=5
        )

        assert len(kept_chunks) == 0
        assert len(overflow_chunks) == 0

    @pytest.mark.asyncio
    async def test_empty_overflow_chunks(self):
        """Test summarization with empty overflow chunks."""

        summary = await self.summarizer.summarize_overflow_chunks([])

        assert summary == ""

    def test_extract_focus_areas_from_query(self):
        """Test focus area extraction from queries."""

        # This would be tested as part of HybridSearch integration
        # since _extract_focus_areas is in that class
        pass

    @pytest.mark.asyncio
    async def test_azure_response_format_handling(self):
        """Test handling of Azure OpenAI response format."""

        overflow_chunks = [
            {"content": "def azure_test(): pass", "metadata": {"file_path": "azure.py"}}
        ]

        # Mock Azure-style response
        with patch("app.services.summarization_service.llm_client") as mock_client:
            mock_response = MagicMock()
            mock_response.choices = None
            mock_response.output = [MagicMock()]
            mock_response.output[0].content = "Azure summary of the code."
            mock_client.complete = AsyncMock(return_value=mock_response)

            summary = await self.summarizer.summarize_overflow_chunks(overflow_chunks)

            assert "## Summary of Additional Context" in summary
            assert "Azure summary" in summary

    @pytest.mark.asyncio
    async def test_conversation_summarization_empty_list(self):
        """Test conversation summarization with empty message list."""

        summary = await self.summarizer.summarize_conversation_history([])

        assert summary == ""

    def test_token_estimation_accuracy(self):
        """Test token estimation for chunking decisions."""

        # Test with known content lengths
        short_chunks = [
            {"content": "short", "score": 0.9, "chunk_id": i}  # ~1 token
            for i in range(10)
        ]

        kept_chunks, overflow_chunks = self.summarizer.should_summarize_chunks(
            short_chunks, max_context_tokens=5, keep_top_n=10
        )

        # Should fit multiple short chunks within token limit
        assert len(kept_chunks) > 1
        assert len(kept_chunks) <= 10
