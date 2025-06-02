# backend/app/models/embedding.py
"""Embedding models for vector search."""
from sqlalchemy import Column, Integer, Float, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict
from app.models.base import Base, TimestampMixin
import numpy as np


class EmbeddingMetadata(Base, TimestampMixin):
    """Metadata for embeddings stored in VSS."""

    __tablename__ = "embedding_metadata"
    __table_args__ = (
        Index("idx_embedding_metadata_document", "document_id"),
        Index("idx_embedding_metadata_project", "project_id"),
        Index("idx_embedding_metadata_hash", "content_hash"),
    )

    rowid = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("code_documents.id"), nullable=False)
    chunk_id = Column(Integer, ForeignKey("code_embeddings.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    content = Column(sa.Text, nullable=False)
    content_hash = Column(sa.String(64), nullable=False)
    metadata = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)

    # Relationships
    document = relationship("CodeDocument")
    chunk = relationship("CodeEmbedding")
    project = relationship("Project")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "rowid": self.rowid,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "project_id": self.project_id,
            "content": self.content[:500],  # Truncate for response
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
