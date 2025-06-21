"""
Knowledge base API router for search and context building.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeEntry,
    ContextBuildRequest,
    ContextResult,
    KnowledgeStats,
    KnowledgeSearchResponse,
    KnowledgeResponse
)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/search")
async def search_knowledge(
    request: KnowledgeSearchRequest,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Search knowledge base for relevant entries."""
    try:
        # Mock knowledge search implementation
        # In production, this would query your vector database or search index

        mock_entries = [
            KnowledgeEntry(
                id="kb_001",
                content="This is relevant information about AI models.",
                title="AI Model Configuration",
                source="documentation",
                category="technical",
                tags=["ai", "models", "configuration"],
                similarity_score=0.85
            ),
            KnowledgeEntry(
                id="kb_002",
                content="Best practices for prompt engineering.",
                title="Prompt Engineering Guide",
                source="guidelines",
                category="best-practices",
                tags=["prompts", "engineering", "guidelines"],
                similarity_score=0.72
            )
        ]

        # Filter based on similarity threshold
        filtered_entries = [
            entry for entry in mock_entries
            if entry.similarity_score >= request.similarity_threshold
        ][:request.limit]

        response_data = KnowledgeSearchResponse(
            results=filtered_entries,
            total_count=len(filtered_entries),
            query_time=0.15,
            has_more=len(mock_entries) > request.limit,
            suggestions=["AI configuration", "model setup", "prompt design"]
        )

        return KnowledgeResponse(
            success=True,
            data=response_data.dict()
        )
    except Exception as e:
        detail = f"Knowledge search failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/context")
async def build_context(
    request: ContextBuildRequest,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Build optimized context from knowledge entries."""
    try:
        # Mock context building implementation
        # In production, this would intelligently combine and optimize content

        # Simulate retrieving knowledge entries
        mock_sources = [
            KnowledgeEntry(
                id=entry_id,
                content=f"Content for entry {entry_id}",
                title=f"Knowledge Entry {entry_id}",
                similarity_score=0.8
            )
            for entry_id in request.knowledge_entries[:3]  # Limit for demo
        ]

        # Build combined context
        combined_content = "\n\n".join([
            f"[{source.title}]\n{source.content}"
            for source in mock_sources
        ])

        # Truncate if needed
        if len(combined_content) > request.max_context_length:
            combined_content = combined_content[:request.max_context_length]
            combined_content += "... [truncated]"

        context_result = ContextResult(
            context=combined_content,
            sources=mock_sources,
            context_length=len(combined_content),
            relevance_score=0.82
        )

        return KnowledgeResponse(
            success=True,
            data=context_result.dict()
        )
    except Exception as e:
        detail = f"Context building failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/stats/{project_id}")
async def get_knowledge_stats(
    project_id: str,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Get knowledge base statistics for a project."""
    try:
        # Mock statistics implementation
        # In production, this would query your database for real stats

        stats = KnowledgeStats(
            total_entries=1250,
            categories={
                "technical": 450,
                "best-practices": 320,
                "examples": 280,
                "troubleshooting": 200
            },
            recent_additions=25,
            search_volume=1840,
            hit_rate=0.73,
            popular_queries=[
                {"query": "AI model setup", "count": 145},
                {"query": "prompt optimization", "count": 98},
                {"query": "error handling", "count": 76}
            ],
            last_updated=datetime.utcnow()
        )

        return KnowledgeResponse(
            success=True,
            data=stats.dict()
        )
    except Exception as e:
        detail = f"Failed to get knowledge stats: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.post("/entries")
async def add_knowledge_entry(
    entry: KnowledgeEntry,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Add a new knowledge base entry."""
    try:
        # Mock entry creation
        # In production, this would store in your database and update
        # search index

        # Generate ID if not provided
        if not entry.id:
            import uuid
            entry.id = f"kb_{uuid.uuid4().hex[:8]}"

        return KnowledgeResponse(
            success=True,
            message="Knowledge entry added successfully",
            data={"entry_id": entry.id}
        )
    except Exception as e:
        detail = f"Failed to add knowledge entry: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/entries/{entry_id}")
async def get_knowledge_entry(
    entry_id: str,
    db: Session = Depends(get_db)
) -> KnowledgeResponse:
    """Get a specific knowledge base entry."""
    try:
        # Mock entry retrieval
        mock_entry = KnowledgeEntry(
            id=entry_id,
            content="This is the content of the knowledge entry.",
            title="Sample Knowledge Entry",
            source="system",
            category="general",
            tags=["sample", "demo"]
        )

        return KnowledgeResponse(
            success=True,
            data=mock_entry.dict()
        )
    except Exception as e:
        detail = f"Failed to get knowledge entry: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


@router.get("/summary/{project_id}")
async def get_project_summary(
    project_id: int,
    _db: Session = Depends(get_db)  # unused, prefixed to silence linter
) -> dict:
    """Get knowledge summary for a specific project."""
    try:
        # Mock implementation - in production, this would query your database
        # and aggregate knowledge base entries for the project

        summary_data = {
            "project_id": project_id,
            "total_documents": 45,
            "total_code_files": 127,
            "last_updated": datetime.utcnow().isoformat(),
            "summary": (
                f"Project {project_id} contains various AI-related "
                f"documentation and code files covering machine learning "
                f"models, data processing pipelines, and API integrations."
            ),
            "key_topics": [
                "Machine Learning",
                "API Development",
                "Data Processing",
                "Authentication",
                "WebSocket Integration"
            ],
            "recent_activity": [
                {
                    "type": "document_added",
                    "title": "WebSocket Implementation Guide",
                    "timestamp": (
                        datetime.utcnow() - timedelta(hours=2)
                    ).isoformat()
                },
                {
                    "type": "code_updated",
                    "title": "Chat Router Updates",
                    "timestamp": (
                        datetime.utcnow() - timedelta(hours=5)
                    ).isoformat()
                }
            ],
            "statistics": {
                "lines_of_code": 12543,
                "documentation_coverage": 78.5,
                "test_coverage": 65.2
            }
        }

        return {
            "success": True,
            "data": summary_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project summary: {str(e)}"
        ) from e
