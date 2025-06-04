# Base model classes and mixins
from sqlalchemy import Column, DateTime, Integer
from datetime import datetime

# Re-use the global Base from app.database so every model registers
# on the same SQLAlchemy metadata.  This avoids split metadata issues
# that prevented essential tables (e.g. *users*) from being created.
from app.database import Base


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps"""

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Record last update timestamp",
    )


class BaseModel(Base):
    """Abstract base model with common fields"""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, comment="Primary key")
