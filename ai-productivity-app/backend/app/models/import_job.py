"""SQLAlchemy model for repository import jobs."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class ImportStatus(str, enum.Enum):
    QUEUED = "queued"
    CLONING = "cloning"
    INDEXING = "indexing"  # chunking + db insert
    EMBEDDING = "embedding"  # vector generation
    COMPLETED = "completed"
    FAILED = "failed"


class ImportJob(Base, TimestampMixin):
    """Track long-running Git import tasks."""

    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True)

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    project = relationship("Project", back_populates="import_jobs")

    requested_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    repo_url = Column(String, nullable=False)
    branch = Column(String, default="main", nullable=False)
    commit_sha = Column(String, nullable=True)

    status = Column(Enum(ImportStatus), default=ImportStatus.QUEUED, nullable=False)
    progress_pct = Column(Integer, default=0, nullable=False)
    error = Column(String, nullable=True)

    # TimestampMixin already provides created_at / updated_at

    def touch(self):  # noqa: D401 – helper
        """Update *updated_at* to now (for manual updates)."""
        self.updated_at = datetime.now(timezone.utc)

    # readable repr for logs / tests
    def __repr__(self) -> str:  # noqa: D401
        return f"<ImportJob id={self.id} project={self.project_id} status={self.status}>"
