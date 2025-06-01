# backend/app/models/code.py
"""Code document and embedding models for storing parsed code and vectors.

Tracks code files, their parsed AST symbols, and embedding chunks for
semantic search capabilities.
"""
from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, Boolean, DateTime, Float, Index
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.mutable import MutableList
from .base import Base, TimestampMixin
import hashlib
from datetime import datetime


class CodeDocument(Base, TimestampMixin):
    """Represents a code file with parsed metadata."""

    __tablename__ = 'code_documents'
    __table_args__ = (
        Index("idx_code_document_project", "project_id"),
        Index("idx_code_document_path", "file_path"),
        Index("idx_code_document_hash", "content_hash"),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey('projects.id', ondelete='CASCADE'),
        nullable=False,
        comment="Associated project"
    )
    file_path = Column(
        String(500),
        nullable=False,
        comment="Relative file path"
    )
    repo_name = Column(
        String(200),
        comment="Repository name if from git"
    )
    commit_sha = Column(
        String(40),
        comment="Git commit SHA"
    )

    # Code metadata
    language = Column(
        String(50),
        comment="Programming language"
    )
    file_size = Column(
        Integer,
        comment="File size in bytes"
    )
    last_modified = Column(
        DateTime,
        comment="File modification time"
    )

    # Parsing results stored as JSON for flexibility
    symbols = Column(
        MutableList.as_mutable(JSON),
        default=list,
        comment="Extracted symbols [{name, type, line_start, line_end}]"
    )
    imports = Column(
        MutableList.as_mutable(JSON),
        default=list,
        comment="Import statements"
    )
    ast_metadata = Column(
        JSON,
        default=dict,
        comment="Additional AST information"
    )

    # Search optimization
    content_hash = Column(
        String(64),
        comment="SHA256 hash of file content"
    )
    is_indexed = Column(
        Boolean,
        default=False,
        comment="Whether embeddings have been generated"
    )

    # Relationships
    project = relationship("Project", back_populates="code_documents")
    embeddings = relationship(
        "CodeEmbedding",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    @validates("file_path")
    def validate_file_path(self, key, file_path):
        """Validate file path."""
        if not file_path or len(file_path.strip()) == 0:
            raise ValueError("File path cannot be empty")
        if len(file_path) > 500:
            raise ValueError("File path cannot exceed 500 characters")
        # Normalize path separators
        return file_path.replace('\\', '/')

    @validates("language")
    def validate_language(self, key, language):
        """Validate supported languages."""
        supported = {'python', 'javascript', 'typescript', 'jsx', 'tsx', None}
        if language and language not in supported:
            raise ValueError(f"Unsupported language: {language}")
        return language

    def __repr__(self):
        return f"<CodeDocument(id={self.id}, path='{self.file_path}', language={self.language})>"


class CodeEmbedding(Base, TimestampMixin):
    """Stores embedding vectors for code chunks."""

    __tablename__ = 'code_embeddings'
    __table_args__ = (
        Index("idx_embedding_document", "document_id"),
        Index("idx_embedding_symbol", "symbol_name"),
    )

    id = Column(Integer, primary_key=True)
    document_id = Column(
        Integer,
        ForeignKey('code_documents.id', ondelete='CASCADE'),
        nullable=False,
        comment="Parent document"
    )

    # Chunk information
    chunk_content = Column(
        Text,
        nullable=False,
        comment="Code chunk text"
    )
    symbol_name = Column(
        String(200),
        comment="Symbol name if applicable"
    )
    symbol_type = Column(
        String(50),
        comment="Symbol type (function, class, method, etc.)"
    )
    start_line = Column(
        Integer,
        comment="Starting line number"
    )
    end_line = Column(
        Integer,
        comment="Ending line number"
    )

    # Embedding data (stored as JSON array for SQLite compatibility)
    embedding = Column(
        JSON,
        comment="Embedding vector as JSON array"
    )
    embedding_model = Column(
        String(50),
        default='text-embedding-3-small',
        comment="Model used for embedding"
    )
    embedding_dim = Column(
        Integer,
        default=1536,
        comment="Embedding dimension"
    )

    # Additional metadata
    tags = Column(
        MutableList.as_mutable(JSON),
        default=list,
        comment="Static analysis tags"
    )
    dependencies = Column(
        JSON,
        comment="Functions/classes this chunk depends on"
    )

    # Relationships
    document = relationship("CodeDocument", back_populates="embeddings")

    @validates("chunk_content")
    def validate_chunk_content(self, key, content):
        """Validate chunk content."""
        if not content or len(content.strip()) == 0:
            raise ValueError("Chunk content cannot be empty")
        # Limit chunk size to prevent huge embeddings
        if len(content) > 10000:
            raise ValueError("Chunk content exceeds maximum size")
        return content

    def __repr__(self):
        return f"<CodeEmbedding(id={self.id}, symbol='{self.symbol_name}', lines={self.start_line}-{self.end_line})>"


# Update Project model relationship
from .project import Project
Project.code_documents = relationship(
    "CodeDocument",
    back_populates="project",
    cascade="all, delete-orphan"
