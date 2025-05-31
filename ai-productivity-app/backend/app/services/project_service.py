"""Business logic layer for project management.

Handles complex project operations, timeline tracking, and statistics.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Optional

from app.models.project import Project, ProjectStatus
from app.models.timeline import TimelineEvent
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectFilters,
    ProjectStats, TimelineEventCreate
)


class ProjectService:
    """Service class for project operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_project_with_timeline(
        self,
        project_data: ProjectCreate,
        user_id: int
    ) -> Project:
        """Create a new project with initial timeline event."""
        # Create project
        project = Project(
            title=project_data.title,
            description=project_data.description,
            status=ProjectStatus(project_data.status),
            color=project_data.color,
            emoji=project_data.emoji,
            tags=project_data.tags,
            owner_id=user_id
        )
        self.db.add(project)
        self.db.flush()  # Get project ID

        # Create initial timeline event
        event = TimelineEvent(
            project_id=project.id,
            event_type=TimelineEvent.EVENT_CREATED,
            title=f"Project '{project.title}' created",
            user_id=user_id
        )
        self.db.add(event)
        self.db.commit()

        return project

    def update_project(
        self,
        project_id: int,
        update_data: ProjectUpdate,
        user_id: int
    ) -> Optional[Project]:
        """Update project and track changes in timeline."""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None

        # Track what changed
        changes = []

        # Update fields
        if update_data.title is not None and update_data.title != project.title:
            changes.append(f"title changed from '{project.title}' to '{update_data.title}'")
            project.title = update_data.title

        if update_data.description is not None:
            project.description = update_data.description
            changes.append("description updated")

        if update_data.status is not None and update_data.status != project.status.value:
            old_status = project.status.value
            project.status = ProjectStatus(update_data.status)
            changes.append(f"status changed from '{old_status}' to '{update_data.status}'")

            # Create status change event
            self.db.add(TimelineEvent(
                project_id=project.id,
                event_type=TimelineEvent.EVENT_STATUS_CHANGED,
                title=f"Status changed to {update_data.status}",
                event_metadata={"old_status": old_status, "new_status": update_data.status},
                user_id=user_id
            ))

        if update_data.color is not None:
            project.color = update_data.color

        if update_data.emoji is not None:
            project.emoji = update_data.emoji

        if update_data.tags is not None:
            project.tags = update_data.tags
            changes.append("tags updated")

        # Create update event if there were changes
        if changes:
            self.db.add(TimelineEvent(
                project_id=project.id,
                event_type=TimelineEvent.EVENT_UPDATED,
                title="Project updated",
                description=", ".join(changes),
                user_id=user_id
            ))

        self.db.commit()
        return project

    def get_projects_with_stats(
        self,
        filters: ProjectFilters
    ) -> tuple[List[Project], int]:
        """Get filtered projects with statistics."""
        query = self.db.query(Project).options(joinedload(Project.owner))

        # Apply filters
        if filters.status:
            query = query.filter(Project.status == ProjectStatus(filters.status))

        if filters.owner_id:
            query = query.filter(Project.owner_id == filters.owner_id)

        if filters.tags:
            # Match any of the provided tags
            tag_filters = []
            for tag in filters.tags:
                tag_filters.append(Project.tags.contains([tag]))
            query = query.filter(or_(*tag_filters))

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Project.title.ilike(search_term),
                    Project.description.ilike(search_term)
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (filters.page - 1) * filters.per_page
        projects = query.offset(offset).limit(filters.per_page).all()

        # Load statistics for each project
        for project in projects:
            project.stats = self._get_project_stats(project.id)

        return projects, total

    def _get_project_stats(self, project_id: int) -> ProjectStats:
        """Calculate statistics for a project."""
        # Count timeline events
        event_count = self.db.query(func.count(TimelineEvent.id)).filter(
            TimelineEvent.project_id == project_id
        ).scalar()

        # Get last activity
        last_event = self.db.query(TimelineEvent.created_at).filter(
            TimelineEvent.project_id == project_id
        ).order_by(TimelineEvent.created_at.desc()).first()

        return ProjectStats(
            files=0,  # Will be implemented in Phase 4
            timeline_events=event_count or 0,
            last_activity=last_event[0] if last_event else None
        )

    def add_timeline_event(
        self,
        project_id: int,
        event_data: TimelineEventCreate,
        user_id: int
    ) -> Optional[TimelineEvent]:
        """Add a custom timeline event to a project."""
        # Verify project exists
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None

        event = TimelineEvent(
            project_id=project_id,
            event_type=event_data.event_type,
            title=event_data.title,
            description=event_data.description,
            event_metadata=event_data.metadata,
            user_id=user_id
        )
        self.db.add(event)
        self.db.commit()

        return event

    def archive_project(self, project_id: int, user_id: int) -> Optional[Project]:
        """Archive a project."""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None

        project.status = ProjectStatus.ARCHIVED

        self.db.add(TimelineEvent(
            project_id=project.id,
            event_type=TimelineEvent.EVENT_STATUS_CHANGED,
            title="Project archived",
            event_metadata={"old_status": "active", "new_status": "archived"},
            user_id=user_id
        ))

        self.db.commit()
        return project
