# backend/app/models/code.py
"""Code document and embedding models for storing parsed code and vectors.

Tracks code files, their parsed AST symbols, and embedding chunks for
semantic search capabilities.
"""
from pathlib import Path, PurePosixPath
import re
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    JSON,
    ForeignKey,
    Boolean,
    DateTime,
    Index,
    CheckConstraint,
)

# Replace *TSVectorType* from the missing *sqlalchemy-utils* package with the
# built-in ``TSVECTOR`` type provided by SQLAlchemy's PostgreSQL dialect.

from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR as TSVectorType
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.mutable import MutableList

from app.config import settings
from app.schemas.errors import ValidationErrorCode, validation_error_response
from .base import Base, TimestampMixin
from .project import Project

# Define upload root from settings
UPLOAD_ROOT = Path(
    settings.upload_root if hasattr(settings, "upload_root") else "./data/uploads"
).resolve()


class CodeDocument(Base, TimestampMixin):
    """Represents a code file with parsed metadata."""

    __tablename__ = "code_documents"
    __table_args__ = (
        # PostgreSQL-specific indexes
        Index("idx_code_documents_project_lang", "project_id", "language"),
        Index("idx_code_documents_hash", "content_hash", postgresql_using="hash"),
        Index("idx_code_documents_symbols_gin", "symbols", postgresql_using="gin"),
        Index("idx_code_documents_imports_gin", "imports", postgresql_using="gin"),
        Index("idx_code_documents_ast_gin", "ast_metadata", postgresql_using="gin"),
        Index("idx_code_documents_search_gin", "search_vector", postgresql_using="gin"),
        Index(
            "idx_code_documents_path_trgm",
            "file_path",
            postgresql_using="gin",
            postgresql_ops={"file_path": "gin_trgm_ops"},
        ),
        # Check constraints for data integrity
        CheckConstraint("file_size >= 0", name="positive_file_size"),
        CheckConstraint("jsonb_typeof(symbols) = 'array'", name="symbols_is_array"),
        CheckConstraint("jsonb_typeof(imports) = 'array'", name="imports_is_array"),
        CheckConstraint(
            "jsonb_typeof(ast_metadata) = 'object'", name="ast_metadata_is_object"
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="Associated project",
    )
    file_path = Column(String(500), nullable=False, comment="Relative file path")
    repo_name = Column(String(200), comment="Repository name if from git")
    commit_sha = Column(String(40), comment="Git commit SHA")

    # Code metadata
    language = Column(String(50), comment="Programming language")
    file_size = Column(Integer, comment="File size in bytes")
    last_modified = Column(DateTime, comment="File modification time")

    # Parsing results stored as JSONB for PostgreSQL optimization
    symbols = Column(
        JSONB,
        default=list,
        comment="Extracted symbols [{name, type, line_start, line_end}]",
    )
    imports = Column(JSONB, default=list, comment="Import statements")
    ast_metadata = Column(JSONB, default=dict, comment="Additional AST information")

    # Full-text search vector for PostgreSQL
    search_vector = Column(
        TSVectorType, comment="Full-text search vector for code content"
    )

    # Search optimization
    content_hash = Column(String(64), comment="SHA256 hash of file content")
    is_indexed = Column(
        Boolean, default=False, comment="Whether embeddings have been generated"
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
                message="File path cannot be empty.",
            )

        if len(file_path) > 500:
            raise validation_error_response(
                code=ValidationErrorCode.FIELD_TOO_LONG,
                field="file_path",
                message="File path cannot exceed 500 characters.",
            )

        # Block Windows drive letters
        if re.match(r"^[A-Za-z]:", file_path):
            raise validation_error_response(
                code=ValidationErrorCode.PATH_NOT_ALLOWED,
                field="file_path",
                message="Windows drive letters are not permitted.",
            )

        # Normalize to POSIX path
        normalized_path = PurePosixPath(file_path).as_posix()

        # Check for any parent directory references
        if ".." in normalized_path:
            raise validation_error_response(
                code=ValidationErrorCode.PATH_NOT_ALLOWED,
                field="file_path",
                message="Parent directory references ('..') are not allowed.",
            )

        # Additional checks for encoded traversal attempts
        dangerous_patterns = [
            "..%2F",
            "..%2f",  # URL encoded forward slash
            "..%5C",
            "..%5c",  # URL encoded backslash
            "%2e%2e",  # URL encoded dots
            "..\\",  # Windows style
            "\\..",  # Reverse Windows style
            ".../",  # Triple dot attempts
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
                    message="Path escapes the upload directory.",
                )
        except Exception:
            raise validation_error_response(
                code=ValidationErrorCode.PATH_NOT_ALLOWED,
                field="file_path",
                message="Invalid path resolution.",
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
            "python",
            "javascript",
            "typescript",
            "jsx",
            "tsx",
            "markdown",
            "json",
            "yaml",
            None,
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

    __tablename__ = "code_embeddings"
    __table_args__ = (
        # PostgreSQL-specific indexes
        Index("idx_code_embeddings_document", "document_id"),
        Index("idx_code_embeddings_symbol", "symbol_name", "symbol_type"),
        Index("idx_code_embeddings_tags_gin", "tags", postgresql_using="gin"),
        Index("idx_code_embeddings_deps_gin", "dependencies", postgresql_using="gin"),
        Index("idx_code_embeddings_model_dim", "embedding_model", "embedding_dim"),
        # Vector indexes will be added via migration when pgvector is available
        # Index('idx_code_embeddings_vector_cosine', 'embedding_vector',
        #       postgresql_using='ivfflat', postgresql_ops={'embedding_vector': 'vector_cosine_ops'}),
        # Check constraints
        CheckConstraint("embedding_dim > 0", name="positive_embedding_dim"),
        CheckConstraint("start_line <= end_line", name="valid_line_range"),
        CheckConstraint("jsonb_typeof(tags) = 'array'", name="tags_is_array"),
        CheckConstraint(
            "jsonb_typeof(dependencies) = 'object'", name="dependencies_is_object"
        ),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True)
    document_id = Column(
        Integer,
        ForeignKey("code_documents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent document",
    )

    # Chunk information
    chunk_content = Column(Text, nullable=False, comment="Code chunk text")
    symbol_name = Column(String(200), comment="Symbol name if applicable")
    symbol_type = Column(
        String(50), comment="Symbol type (function, class, method, etc.)"
    )
    start_line = Column(Integer, comment="Starting line number")
    end_line = Column(Integer, comment="Ending line number")

    # Embedding data (JSON for SQLite compatibility, will add pgvector column via migration)
    embedding = Column(
        JSON, comment="Embedding vector as JSON array (legacy compatibility)"
    )

    # pgvector support will be added via migration
    # embedding_vector = Column(Vector(1536), comment="Native PostgreSQL vector")

    embedding_model = Column(
        String(50), default="text-embedding-3-small", comment="Model used for embedding"
    )
    embedding_dim = Column(Integer, default=1536, comment="Embedding dimension")

    # Additional metadata as JSONB for better performance
    tags = Column(JSONB, default=list, comment="Static analysis tags")
    dependencies = Column(
        JSONB, default=dict, comment="Functions/classes this chunk depends on"
    )

    # Relationships
    document = relationship("CodeDocument", back_populates="embeddings")

    @validates("chunk_content")
    def validate_chunk_content(self, key, content):
        """Validate chunk content."""
        if not content or len(content.strip()) == 0:
            raise ValueError("Chunk content cannot be empty")
        # Limit chunk size to prevent huge embeddings.  Empirically we found
        # that the previous 10 kB threshold was too strict for files that are
        # still handled well by the embedding model.  Increase to 32 kB which
        # corresponds to the maximum context length of most modern models
        # while keeping a guardrail against pathological inputs.
        if len(content) > 32000:
            raise ValueError("Chunk content exceeds maximum size (32 k cap)")
        return content

    def __repr__(self):
        return (
            f"<CodeEmbedding(id={self.id}, symbol='{self.symbol_name}', "
            f"lines={self.start_line}-{self.end_line})>"
        )


# Update Project model relationship
Project.code_documents = relationship(
    "CodeDocument", back_populates="project", cascade="all, delete-orphan"
)
