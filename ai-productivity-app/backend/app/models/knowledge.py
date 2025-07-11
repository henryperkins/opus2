"""Knowledge document models for storing full-text knowledge base entries."""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship, validates

from .base import Base, TimestampMixin
from .project import Project


class KnowledgeDocument(Base, TimestampMixin):
    """Represents a knowledge base document with full content."""

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        # Indexes for efficient queries
        Index("idx_knowledge_project", "project_id"),
        Index("idx_knowledge_title", "title"),
        {"extend_existing": True},
    )

    id = Column(String(100), primary_key=True, comment="Unique knowledge entry ID")
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="Associated project",
    )
    content = Column(Text, nullable=False, comment="Full knowledge document content")
    title = Column(String(500), nullable=False, comment="Document title")
    source = Column(String(500), comment="Source of the knowledge (file, URL, etc.)")
    category = Column(String(100), comment="Knowledge category")

    # Relationships
    project = relationship("Project", back_populates="knowledge_documents")

    @validates("content")
    def validate_content(self, key, content):
        """Validate content field."""
        if not content or len(content.strip()) == 0:
            raise ValueError("Knowledge content cannot be empty")
        return content

    @validates("title")
    def validate_title(self, key, title):
        """Validate title field."""
        if not title or len(title.strip()) == 0:
            raise ValueError("Knowledge title cannot be empty")
        if len(title) > 500:
            raise ValueError("Knowledge title cannot exceed 500 characters")
        return title

    def __repr__(self):
        return f"<KnowledgeDocument(id='{self.id}', title='{self.title}', project_id={self.project_id})>"


# Update Project model relationship
Project.knowledge_documents = relationship(
    "KnowledgeDocument", back_populates="project", cascade="all, delete-orphan"
)
