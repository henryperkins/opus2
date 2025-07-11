"""Integration tests for user feedback system."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.models.feedback import UserFeedback, FeedbackSummary
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.models.project import Project


@pytest.mark.asyncio
async def test_feedback_creation(
    async_client: AsyncClient, test_user: User, test_session: AsyncSession
):
    """Test creating feedback for a message."""

    # Create a project and chat session
    project = Project(name="Test Project", description="Test", user_id=test_user.id)
    test_session.add(project)
    await test_session.flush()

    chat_session = ChatSession(project_id=project.id, title="Test Chat")
    test_session.add(chat_session)
    await test_session.flush()

    # Create an assistant message
    message = ChatMessage(
        session_id=chat_session.id,
        user_id=test_user.id,
        role="assistant",
        content="This is a test response with some code examples.",
        rag_used=True,
        rag_confidence=0.8,
        knowledge_sources_count=3,
    )
    test_session.add(message)
    await test_session.commit()

    # Create feedback
    feedback_data = {
        "message_id": message.id,
        "rating": 4,
        "helpful": True,
        "comments": "Very helpful response!",
        "accuracy_rating": 5,
        "clarity_rating": 4,
        "completeness_rating": 4,
    }

    response = await async_client.post("/api/feedback/", json=feedback_data)

    assert response.status_code == 200
    feedback_response = response.json()

    assert feedback_response["message_id"] == message.id
    assert feedback_response["rating"] == 4
    assert feedback_response["helpful"] is True
    assert feedback_response["comments"] == "Very helpful response!"
    assert feedback_response["accuracy_rating"] == 5


@pytest.mark.asyncio
async def test_feedback_stats(
    async_client: AsyncClient, test_user: User, test_session: AsyncSession
):
    """Test feedback statistics aggregation."""

    # Create test data
    project = Project(name="Test Project", description="Test", user_id=test_user.id)
    test_session.add(project)
    await test_session.flush()

    chat_session = ChatSession(project_id=project.id, title="Test Chat")
    test_session.add(chat_session)
    await test_session.flush()

    # Create multiple feedback entries
    for i in range(5):
        message = ChatMessage(
            session_id=chat_session.id,
            user_id=test_user.id,
            role="assistant",
            content=f"Test response {i}",
            rag_used=True,
            rag_confidence=0.7 + (i * 0.05),
        )
        test_session.add(message)
        await test_session.flush()

        feedback = UserFeedback(
            message_id=message.id,
            user_id=test_user.id,
            session_id=chat_session.id,
            rating=3 + (i % 3),  # Ratings 3-5
            helpful=i % 2 == 0,  # Alternating helpful/not helpful
            rag_was_used=True,
            rag_confidence=0.7 + (i * 0.05),
        )
        test_session.add(feedback)

    await test_session.commit()

    # Get statistics
    response = await async_client.get("/api/feedback/stats?days=30")

    assert response.status_code == 200
    stats = response.json()

    assert stats["total_count"] == 5
    assert stats["average_rating"] > 3.0
    assert stats["helpful_percentage"] == 60.0  # 3 out of 5 marked helpful
    assert stats["rag_success_rate"] == 60.0


@pytest.mark.asyncio
async def test_feedback_update(
    async_client: AsyncClient, test_user: User, test_session: AsyncSession
):
    """Test updating existing feedback."""

    # Create test data
    project = Project(name="Test Project", description="Test", user_id=test_user.id)
    test_session.add(project)
    await test_session.flush()

    chat_session = ChatSession(project_id=project.id, title="Test Chat")
    test_session.add(chat_session)
    await test_session.flush()

    message = ChatMessage(
        session_id=chat_session.id,
        user_id=test_user.id,
        role="assistant",
        content="Test response",
    )
    test_session.add(message)
    await test_session.commit()

    # Create initial feedback
    feedback_data = {"message_id": message.id, "rating": 3, "helpful": False}

    response = await async_client.post("/api/feedback/", json=feedback_data)
    assert response.status_code == 200

    # Update feedback (should update existing, not create new)
    updated_feedback_data = {
        "message_id": message.id,
        "rating": 5,
        "helpful": True,
        "comments": "Actually, this was very helpful!",
    }

    response = await async_client.post("/api/feedback/", json=updated_feedback_data)
    assert response.status_code == 200

    feedback_response = response.json()
    assert feedback_response["rating"] == 5
    assert feedback_response["helpful"] is True
    assert feedback_response["comments"] == "Actually, this was very helpful!"


@pytest.mark.asyncio
async def test_confidence_warnings_integration(test_session: AsyncSession):
    """Test confidence warning generation with various scenarios."""

    from app.chat.processor import ChatProcessor

    processor = ChatProcessor(test_session)

    # Test low confidence warning
    context_low_confidence = {
        "rag_metadata": {
            "rag_used": True,
            "rag_confidence": 0.2,
            "rag_status": "poor",
            "knowledge_sources_count": 1,
        }
    }

    response = "This is a test response."
    enhanced_response = await processor._add_confidence_warnings(
        response, context_low_confidence
    )

    assert "⚠️ **Low Confidence**" in enhanced_response
    assert "⚠️ **Limited Sources**" in enhanced_response
    assert "ℹ️ **Single Source**" in enhanced_response

    # Test no RAG warning
    context_no_rag = {"rag_metadata": {"rag_used": False}}

    general_response = (
        "Generally speaking, you should implement this feature carefully."
    )
    enhanced_response = await processor._add_confidence_warnings(
        general_response, context_no_rag
    )

    assert (
        "based on general knowledge rather than specific documentation"
        in enhanced_response
    )


@pytest.mark.asyncio
async def test_content_filtering_integration(test_session: AsyncSession):
    """Test content filtering in context building."""

    from app.chat.context_builder import ContextBuilder
    from app.services.content_filter import content_filter

    builder = ContextBuilder(test_session)

    # Test filtering chunks with secrets
    test_chunks = [
        {"content": "This is safe content", "metadata": {"file_path": "safe_file.py"}},
        {
            "content": "API_KEY = 'sk-1234567890abcdefghijklmnopqrstuvwxyz' # Secret key",
            "metadata": {"file_path": "config.py"},
        },
    ]

    filtered_chunks, warnings = content_filter.filter_and_validate_chunks(test_chunks)

    assert len(filtered_chunks) == 2
    assert "[REDACTED API Key]" in filtered_chunks[1]["content"]
    assert len(warnings) > 0
    assert "Redacted content" in warnings[0]


@pytest.mark.asyncio
async def test_summarization_integration():
    """Test summarization service with overflow content."""

    from app.services.summarization_service import SummarizationService

    summarizer = SummarizationService()

    # Test chunk overflow determination
    large_chunks = [
        {
            "content": "This is a large chunk of code" * 100,
            "score": 0.9,
            "chunk_id": i,
            "metadata": {"file_path": f"file_{i}.py"},
        }
        for i in range(10)
    ]

    kept_chunks, overflow_chunks = summarizer.should_summarize_chunks(
        large_chunks, max_context_tokens=1000, keep_top_n=3
    )

    assert len(kept_chunks) <= 3
    assert len(overflow_chunks) > 0
    assert kept_chunks[0]["score"] >= kept_chunks[-1]["score"]  # Sorted by score


@pytest.mark.asyncio
async def test_dynamic_ranking_integration():
    """Test dynamic ranking based on query type detection."""

    from app.services.hybrid_search import HybridSearch
    from unittest.mock import Mock

    # Mock dependencies
    db = Mock()
    vector_service = Mock()
    embedding_generator = Mock()

    search = HybridSearch(db, vector_service, embedding_generator)

    # Test query type detection
    error_query = "I'm getting a TypeError when running this function"
    query_type = search._detect_query_type(error_query)
    assert query_type == "error_debug"

    api_query = "How do I call the REST API endpoint for user registration?"
    query_type = search._detect_query_type(api_query)
    assert query_type == "api_usage"

    conceptual_query = "What is the difference between async and sync programming?"
    query_type = search._detect_query_type(conceptual_query)
    assert query_type == "conceptual"

    specific_query = "Where is the UserService.authenticate() method defined?"
    query_type = search._detect_query_type(specific_query)
    assert query_type == "specific_code"


@pytest.mark.asyncio
async def test_new_tools_registration():
    """Test that new tools are properly registered."""

    from app.llm.tools import _HANDLERS, TOOL_SCHEMAS

    # Check that new tools are registered
    assert "search_commits" in _HANDLERS
    assert "git_blame" in _HANDLERS
    assert "analyze_code_quality" in _HANDLERS

    # Check that schemas exist
    tool_names = [schema["function"]["name"] for schema in TOOL_SCHEMAS]
    assert "search_commits" in tool_names
    assert "git_blame" in tool_names
    assert "analyze_code_quality" in tool_names


@pytest.mark.asyncio
async def test_tool_argument_validation():
    """Test tool argument validation."""

    from app.llm.tools import _validate_tool_arguments

    # Test valid arguments
    valid_args = {"query": "fix authentication", "project_id": 123, "limit": 10}

    error = _validate_tool_arguments("search_commits", valid_args)
    assert error is None

    # Test invalid arguments (missing required field)
    invalid_args = {
        "query": "fix authentication"
        # Missing project_id
    }

    error = _validate_tool_arguments("search_commits", invalid_args)
    assert error is not None
    assert "Missing required parameter: project_id" in error

    # Test wrong type
    wrong_type_args = {
        "query": "fix authentication",
        "project_id": "not_an_integer",  # Should be int
        "limit": 10,
    }

    error = _validate_tool_arguments("search_commits", wrong_type_args)
    assert error is not None
    assert "must be an integer" in error
