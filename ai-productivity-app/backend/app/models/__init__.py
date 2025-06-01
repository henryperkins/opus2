# Model package exports
from .base import Base, TimestampMixin
from .user import User
# Import Phase-4 models so they are registered with SQLAlchemy before metadata
# creation.  These imports must remain *after* Base to avoid circular deps.
from .project import Project, ProjectStatus
from .code import CodeDocument, CodeEmbedding

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Project",
    "ProjectStatus",
    "CodeDocument",
    "CodeEmbedding",
]
