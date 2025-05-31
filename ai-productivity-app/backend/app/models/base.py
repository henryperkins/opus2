# Base model classes and mixins
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer
from datetime import datetime

# Base model for all database models
Base = declarative_base()


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
