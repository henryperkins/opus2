"""Project management API endpoints.

Provides CRUD operations for projects, timeline events, and filtering.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.dependencies import DatabaseDep, CurrentUserRequired, CurrentUserOptional
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.timeline import TimelineEvent
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectFilters,
    TimelineEventCreate,
    TimelineEventResponse,
    UserInfo,
)
from app.services.project_service import ProjectService

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
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
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
    per_page: int = Query(20, ge=1, le=100),
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
        per_page=per_page,
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
            stats=project.stats,
        )
        items.append(item)

    return ProjectListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate, current_user: CurrentUserRequired, db: DatabaseDep
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
        updated_at=project.updated_at,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int, current_user: CurrentUserRequired, db: DatabaseDep
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
        stats=stats,
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    update_data: ProjectUpdate,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Update project details."""
    # Check project exists
    project = get_project_or_404(project_id, db)

    # Check authorization (for small team, all users can modify)
    if not project.can_modify(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this project",
        )

    service = ProjectService(db)
    updated_project = service.update_project(project_id, update_data, current_user.id)

    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
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
        updated_at=updated_project.updated_at,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int, current_user: CurrentUserRequired, db: DatabaseDep
):
    """Delete a project and all associated data."""
    project = get_project_or_404(project_id, db)

    # Check authorization
    if not project.can_modify(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project",
        )

    db.delete(project)
    db.commit()


@router.get("/{project_id}/timeline", response_model=List[TimelineEventResponse])
async def get_project_timeline(
    project_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get project timeline events."""
    # Verify project exists
    get_project_or_404(project_id, db)

    events = (
        db.query(TimelineEvent)
        .filter(TimelineEvent.project_id == project_id)
        .order_by(TimelineEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        TimelineEventResponse(
            id=event.id,
            project_id=event.project_id,
            event_type=event.event_type,
            title=event.title,
            description=event.description,
            metadata=event.event_metadata or {},
            user=serialize_user(event.user) if event.user else None,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.post(
    "/{project_id}/timeline",
    response_model=TimelineEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_timeline_event(
    project_id: int,
    event_data: TimelineEventCreate,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
):
    """Add a custom timeline event to a project."""
    # Verify project exists
    project = get_project_or_404(project_id, db)

    # Check authorization
    if not project.can_modify(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add events to this project",
        )

    service = ProjectService(db)
    event = service.add_timeline_event(project_id, event_data, current_user.id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    return TimelineEventResponse(
        id=event.id,
        project_id=event.project_id,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        metadata=event.event_metadata or {},
        user=serialize_user(event.user) if event.user else None,
        created_at=event.created_at,
    )


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: int, current_user: CurrentUserRequired, db: DatabaseDep
):
    """Archive a project."""
    project = get_project_or_404(project_id, db)

    # Check authorization
    if not project.can_modify(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to archive this project",
        )

    service = ProjectService(db)
    archived_project = service.archive_project(project_id, current_user.id)

    if not archived_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
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
        updated_at=archived_project.updated_at,
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










