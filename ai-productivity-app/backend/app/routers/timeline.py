"""Aggregated timeline API endpoints.

Returns recent timeline events across **all** projects the authenticated
user has access to (currently: projects they own).  This powers the
Activity-log view in the frontend.
"""

from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import DatabaseDep, CurrentUserRequired
from app.models.timeline import TimelineEvent
from app.models.project import Project
from app.schemas.project import TimelineEventResponse, UserInfo

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@router.get("", response_model=List[TimelineEventResponse])
def list_timeline_events(
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Return recent timeline events across all projects the user owns."""

    events = (
        db.query(TimelineEvent)
        .join(Project, Project.id == TimelineEvent.project_id)
        .filter(Project.owner_id == current_user.id)
        .order_by(TimelineEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    def _serialize(event: TimelineEvent) -> TimelineEventResponse:
        return TimelineEventResponse(
            id=event.id,
            project_id=event.project_id,
            event_type=event.event_type,
            title=event.title,
            description=event.description,
            metadata=event.event_metadata or {},
            user=UserInfo(
                id=event.user.id,
                username=event.user.username,
                email=event.user.email,
            ) if event.user else None,
            created_at=event.created_at,
        )

    return [_serialize(e) for e in events]
