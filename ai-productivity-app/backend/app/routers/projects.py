"""Project management API endpoints.

Provides CRUD operations for projects, timeline events, and filtering.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.dependencies import DatabaseDep, CurrentUserRequired, CurrentUserOptional
from app.models.user import User
from app.models.project import Project
from app.models.timeline import TimelineEvent
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectListResponse, ProjectFilters,
    TimelineEventCreate, TimelineEventResponse,
    UserInfo
)
from app.schemas.search import SuggestionsResponse
from app.services.project_service import ProjectService
from app.services.vector_service import get_vector_service
from app.services.hybrid_search import HybridSearch
from app.embeddings.generator import EmbeddingGenerator
from app.config import settings

import logging

router = APIRouter(prefix="/api/projects", tags=["projects"])

# ---------------------------------------------------------------------------
# Module level logger – INFO by default so that the main application picks it
# up with the standard Uvicorn/Gunicorn configuration.
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


def get_project_or_404(project_id: int, db: Session) -> Project:
    """Get project by ID or raise 404."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


def serialize_user(user: User) -> UserInfo:
    """Convert User model to UserInfo schema."""
    return UserInfo(id=user.id, username=user.username, email=user.email)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    status: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    search: Optional[str] = None,
    owner_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """List all projects with filtering and pagination."""
    logger.info(
        "Listing projects – user_id=%s status=%s tags=%s search=%s owner_id=%s page=%s per_page=%s",
        current_user.id,
        status,
        tags,
        search,
        owner_id,
        page,
        per_page,
    )

    filters = ProjectFilters(
        status=status,
        tags=tags,
        search=search,
        owner_id=owner_id,
        page=page,
        per_page=per_page
    )

    service = ProjectService(db)
    projects, total = service.get_projects_with_stats(filters)

    logger.debug("Retrieved %s projects (total=%s)", len(projects), total)

    # Serialize projects
    items = []
    for project in projects:
        item = ProjectResponse(
            id=project.id,
            title=project.title,
            description=project.description,
            status=project.status.value,
            color=project.color,
            emoji=project.emoji,
            tags=project.tags,
            owner=serialize_user(project.owner),
            created_at=project.created_at,
            updated_at=project.updated_at,
            stats=project.stats
        )
        items.append(item)

    return ProjectListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Create a new project."""
    service = ProjectService(db)
    project = service.create_project_with_timeline(project_data, current_user.id)

    # Load owner relationship
    db.refresh(project)

    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        status=project.status.value,
        color=project.color,
        emoji=project.emoji,
        tags=project.tags,
        owner=serialize_user(project.owner),
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Get project details."""
    project = get_project_or_404(project_id, db)
    service = ProjectService(db)
    stats = service._get_project_stats(project.id)

    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        status=project.status.value,
        color=project.color,
        emoji=project.emoji,
        tags=project.tags,
        owner=serialize_user(project.owner),
        created_at=project.created_at,
        updated_at=project.updated_at,
        stats=stats
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    update_data: ProjectUpdate,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Update project details."""
    # Check project exists
    project = get_project_or_404(project_id, db)

    # Check authorization (for small team, all users can modify)
    if not project.can_modify(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this project"
        )

    service = ProjectService(db)
    updated_project = service.update_project(project_id, update_data, current_user.id)

    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return ProjectResponse(
        id=updated_project.id,
        title=updated_project.title,
        description=updated_project.description,
        status=updated_project.status.value,
        color=updated_project.color,
        emoji=updated_project.emoji,
        tags=updated_project.tags,
        owner=serialize_user(updated_project.owner),
        created_at=updated_project.created_at,
        updated_at=updated_project.updated_at
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Delete a project and all associated data."""
    project = get_project_or_404(project_id, db)

    # Check authorization
    if not project.can_modify(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project"
        )

    db.delete(project)
    db.commit()


@router.get("/{project_id}/timeline", response_model=List[TimelineEventResponse])
async def get_project_timeline(
    project_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get project timeline events."""
    # Verify project exists
    get_project_or_404(project_id, db)

    events = db.query(TimelineEvent).filter(
        TimelineEvent.project_id == project_id
    ).order_by(
        TimelineEvent.created_at.desc()
    ).offset(offset).limit(limit).all()

    return [
        TimelineEventResponse(
            id=event.id,
            project_id=event.project_id,
            event_type=event.event_type,
            title=event.title,
            description=event.description,
            metadata=event.event_metadata or {},
            user=serialize_user(event.user) if event.user else None,
            created_at=event.created_at
        )
        for event in events
    ]


@router.post(
    "/{project_id}/timeline",
    response_model=TimelineEventResponse,
    status_code=status.HTTP_201_CREATED
)
async def add_timeline_event(
    project_id: int,
    event_data: TimelineEventCreate,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Add a custom timeline event to a project."""
    # Verify project exists
    project = get_project_or_404(project_id, db)

    # Check authorization
    if not project.can_modify(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add events to this project"
        )

    service = ProjectService(db)
    event = service.add_timeline_event(project_id, event_data, current_user.id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return TimelineEventResponse(
        id=event.id,
        project_id=event.project_id,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        metadata=event.event_metadata or {},
        user=serialize_user(event.user) if event.user else None,
        created_at=event.created_at
    )


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Archive a project."""
    project = get_project_or_404(project_id, db)

    # Check authorization
    if not project.can_modify(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to archive this project"
        )

    service = ProjectService(db)
    archived_project = service.archive_project(project_id, current_user.id)

    if not archived_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return ProjectResponse(
        id=archived_project.id,
        title=archived_project.title,
        description=archived_project.description,
        status=archived_project.status.value,
        color=archived_project.color,
        emoji=archived_project.emoji,
        tags=archived_project.tags,
        owner=serialize_user(archived_project.owner),
        created_at=archived_project.created_at,
        updated_at=archived_project.updated_at
    )


# ---------------------------------------------------------------------------
# Unarchive endpoint (Sprint-1 Ticket 1.3)
# ---------------------------------------------------------------------------


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
async def unarchive_project(
    project_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Set project status back to *active* and log timeline event."""

    project = get_project_or_404(project_id, db)

    if not project.can_modify(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to unarchive this project",
        )

    service = ProjectService(db)
    unarchived = service.unarchive_project(project_id, current_user.id)

    if not unarchived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return ProjectResponse(
        id=unarchived.id,
        title=unarchived.title,
        description=unarchived.description,
        status=unarchived.status.value,
        color=unarchived.color,
        emoji=unarchived.emoji,
        tags=unarchived.tags,
        owner=serialize_user(unarchived.owner),
        created_at=unarchived.created_at,
        updated_at=unarchived.updated_at,
    )


# ---------------------------------------------------------------------------
# Project-scoped search endpoints to match frontend expectations
# ---------------------------------------------------------------------------

@router.post("/{project_id}/search/documents")
async def search_project_documents(
    project_id: int,
    request: dict,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Search documents within a specific project."""
    # Verify project exists and user has access
    project = get_project_or_404(project_id, db)
    
    # Import here to avoid circular imports
    from app.schemas.search import SearchRequest, SearchResponse
    from app.services.hybrid_search import HybridSearch
    from app.services.vector_service import vector_service
    from app.embeddings.generator import EmbeddingGenerator
    
    # Create search request with project scope
    search_request = SearchRequest(
        query=request.get("query", ""),
        project_ids=[project_id],
        search_types=["documents"],
        limit=request.get("limit", 10),
        filters=request.get("filters", {})
    )
    
    # Execute search
    embedding_generator = EmbeddingGenerator()
    hybrid_search = HybridSearch(db, vector_service, embedding_generator)
    
    try:
        results = await hybrid_search.search(
            query=search_request.query,
            project_ids=search_request.project_ids,
            filters=search_request.filters,
            limit=search_request.limit,
            search_types=search_request.search_types,
        )
        return {"results": results.results, "total": results.total}
    except Exception as e:
        logger.error(f"Document search failed for project {project_id}: {e}")
        return {"results": [], "total": 0}


@router.post("/{project_id}/search/code")
async def search_project_code(
    project_id: int,
    request: dict,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Search code within a specific project."""
    # Verify project exists and user has access
    project = get_project_or_404(project_id, db)
    
    # Import here to avoid circular imports
    from app.schemas.search import SearchRequest, SearchResponse
    from app.services.hybrid_search import HybridSearch
    from app.services.vector_service import vector_service
    from app.embeddings.generator import EmbeddingGenerator
    
    # Create search request with project scope
    search_request = SearchRequest(
        query=request.get("query", ""),
        project_ids=[project_id],
        search_types=["code"],
        limit=request.get("limit", 10),
        filters=request.get("filters", {})
    )
    
    # Execute search
    embedding_generator = EmbeddingGenerator()
    hybrid_search = HybridSearch(db, vector_service, embedding_generator)
    
    try:
        results = await hybrid_search.search(search_request)
        return {"results": results.results, "total": results.total}
    except Exception as e:
        logger.error(f"Code search failed for project {project_id}: {e}")
        return {"results": [], "total": 0}


@router.post("/{project_id}/search/hybrid")
async def search_project_hybrid(
    project_id: int,
    request: dict,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Hybrid search across all content types within a specific project."""
    # Verify project exists and user has access
    project = get_project_or_404(project_id, db)
    
    # Import here to avoid circular imports
    from app.schemas.search import SearchRequest, SearchResponse
    from app.services.hybrid_search import HybridSearch
    from app.services.vector_service import vector_service
    from app.embeddings.generator import EmbeddingGenerator
    
    # Create search request with project scope
    search_request = SearchRequest(
        query=request.get("query", ""),
        project_ids=[project_id],
        limit=request.get("limit", 10),
        filters=request.get("filters", {})
    )
    
    # Execute search
    embedding_generator = EmbeddingGenerator()
    hybrid_search = HybridSearch(db, vector_service, embedding_generator)
    
    try:
        results = await hybrid_search.search(search_request)
        return {"results": results.results, "total": results.total}
    except Exception as e:
        logger.error(f"Hybrid search failed for project {project_id}: {e}")
        return {"results": [], "total": 0}


@router.post("/{project_id}/search/similar")
async def find_similar_content(
    project_id: int,
    request: dict,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Find content similar to provided text within a specific project."""
    # Verify project exists and user has access
    project = get_project_or_404(project_id, db)
    
    content = request.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Content is required for similarity search")
    
    # Import here to avoid circular imports
    from app.schemas.search import SearchRequest, SearchResponse
    from app.services.hybrid_search import HybridSearch
    from app.services.vector_service import vector_service
    from app.embeddings.generator import EmbeddingGenerator
    
    # Create search request for similarity
    search_request = SearchRequest(
        query=content,
        project_ids=[project_id],
        limit=request.get("limit", 10),
        filters=request.get("filters", {}),
        threshold=request.get("threshold", 0.7)
    )
    
    # Execute search
    embedding_generator = EmbeddingGenerator()
    hybrid_search = HybridSearch(db, vector_service, embedding_generator)
    
    try:
        results = await hybrid_search.search(search_request)
        return {"items": results.results, "total": results.total}
    except Exception as e:
        logger.error(f"Similarity search failed for project {project_id}: {e}")
        return {"items": [], "total": 0}


@router.get(
    "/{project_id}/search/suggestions",
    dependencies=[Depends(CurrentUserOptional)],
    response_model=SuggestionsResponse,
)
async def project_suggestions(
    project_id: int,
    db: DatabaseDep,
    q: str = Query(..., min_length=2, alias="q"),
    limit: int = Query(5, le=25),
):
    """Get search suggestions for a project."""
    try:
        # Get the project (raises 404 if not found)
        project = get_project_or_404(project_id, db)
        
        # Initialize services
        vector_service = await get_vector_service()
        embedding_generator = EmbeddingGenerator()
        hybrid_search = HybridSearch(db, vector_service, embedding_generator)
        
        # Execute search with keyword search only for suggestions
        results = await hybrid_search.search(
            query=q,
            project_ids=[project_id],
            limit=limit,
            search_types=["keyword"]
        )
        
        # Extract suggestion strings from results
        suggestions = [result.get("content", "")[:100] for result in results if result.get("content")]
        
        return {"suggestions": suggestions}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get suggestions for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get suggestions")
