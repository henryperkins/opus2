# backend/app/models/code.py
"""Code document and embedding models for storing parsed code and vectors.

Tracks code files, their parsed AST symbols, and embedding chunks for
semantic search capabilities.
"""
from pathlib import Path, PurePosixPath
import re
from sqlalchemy import (
    Column, Integer, String, Text, JSON, ForeignKey, Boolean, DateTime
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.mutable import MutableList

from app.config import settings
from app.schemas.errors import ValidationErrorCode, validation_error_response
from .base import Base, TimestampMixin
from .project import Project

# Define upload root from settings
UPLOAD_ROOT = Path(
    settings.upload_root if hasattr(settings, 'upload_root')
    else './data/uploads'
).resolve()


class CodeDocument(Base, TimestampMixin):
    """Represents a code file with parsed metadata."""

    __tablename__ = 'code_documents'
    __table_args__ = (
        {"extend_existing": True},
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
        cascade="all, delete-orphan",
    )

    @validates("file_path")
    def validate_file_path(self, key, file_path):
        """Validate file path against directory traversal and other attacks."""
        if not file_path or len(file_path.strip()) == 0:
            raise validation_error_response(
                code=ValidationErrorCode.FIELD_REQUIRED,
                field="file_path",
                message="File path cannot be empty."
            )

        if len(file_path) > 500:
            raise validation_error_response(
                code=ValidationErrorCode.FIELD_TOO_LONG,
                field="file_path",
                message="File path cannot exceed 500 characters."
            )

        # Block Windows drive letters
        if re.match(r'^[A-Za-z]:', file_path):
            raise validation_error_response(
                code=ValidationErrorCode.PATH_NOT_ALLOWED,
                field="file_path",
                message="Windows drive letters are not permitted."
            )

        # Normalize to POSIX path
        normalized_path = PurePosixPath(file_path).as_posix()

        # Check for any parent directory references
        if '..' in normalized_path:
            raise validation_error_response(
                code=ValidationErrorCode.PATH_NOT_ALLOWED,
                field="file_path",
                message="Parent directory references ('..') are not allowed."
            )

        # Additional checks for encoded traversal attempts
        dangerous_patterns = [
            '..%2F', '..%2f',  # URL encoded forward slash
            '..%5C', '..%5c',  # URL encoded backslash
            '%2e%2e',          # URL encoded dots
            '..\\',            # Windows style
            '\\..',            # Reverse Windows style
            '.../',            # Triple dot attempts
        ]

        for pattern in dangerous_patterns:
            if pattern in file_path:
                raise validation_error_response(
                    code=ValidationErrorCode.PATH_NOT_ALLOWED,
                    field="file_path",
                    message=f"Encoded traversal pattern ('{pattern}') detected.",
                )

        # Resolve full path and ensure it's within upload root
        try:
            full_path = (UPLOAD_ROOT / normalized_path).resolve()
            if not str(full_path).startswith(str(UPLOAD_ROOT)):
                raise validation_error_response(
                    code=ValidationErrorCode.PATH_NOT_ALLOWED,
                    field="file_path",
                    message="Path escapes the upload directory."
                )
        except Exception:
            raise validation_error_response(
                code=ValidationErrorCode.PATH_NOT_ALLOWED,
                field="file_path",
                message="Invalid path resolution."
            )
        return normalized_path

    @validates("language")
    def validate_language(self, key, language):
        """Validate supported languages."""
        # Supported for *storage* – some languages might not yet be parsed,
        # but we still want to keep the label so we can enable processing
        # later.  Only python / javascript / typescript are currently parsed
        # by the CodeParser; others are ignored during background processing.
        supported = {
            'python', 'javascript', 'typescript', 'jsx', 'tsx',
            'markdown', 'json', 'yaml', None
        }
        if language and language not in supported:
            raise ValueError(f"Unsupported language: {language}")
        return language

    def __repr__(self):
        return (
            f"<CodeDocument(id={self.id}, path='{self.file_path}', "
            f"language={self.language})>"
        )


class CodeEmbedding(Base, TimestampMixin):
    """Stores embedding vectors for code chunks."""

    __tablename__ = 'code_embeddings'
    __table_args__ = (
        {"extend_existing": True},
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
        return (
            f"<CodeEmbedding(id={self.id}, symbol='{self.symbol_name}', "
            f"lines={self.start_line}-{self.end_line})>"
        )


# Update Project model relationship
Project.code_documents = relationship(
    "CodeDocument",
    back_populates="project",
    cascade="all, delete-orphan"
)
