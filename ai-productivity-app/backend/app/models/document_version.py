"""Document version control and change tracking models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class DocumentVersion(Base):
    """Track versions of documents with change history."""
    __tablename__ = "document_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("code_documents.id"), nullable=False)
    version_number = Column(Integer, nullable=False)  # Incremental version
    content_hash = Column(String(64), nullable=False)  # SHA256 of content
    content_size = Column(Integer, nullable=False)
    
    # Change tracking
    change_type = Column(String(20), nullable=False)  # created, modified, deleted
    change_summary = Column(Text, nullable=True)  # Brief description of changes
    changed_by = Column(String(100), nullable=True)  # User or system that made change
    change_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Diff information
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)
    lines_modified = Column(Integer, default=0)
    
    # Metadata
    commit_hash = Column(String(40), nullable=True)  # Git commit hash if available
    branch_name = Column(String(100), nullable=True)  # Git branch
    tags = Column(JSON, nullable=True)  # Version tags like "stable", "beta"
    
    # Relationships
    document = relationship("CodeDocument", back_populates="versions")
    changes = relationship("DocumentChange", back_populates="version")
    
    def __repr__(self):
        return f"<DocumentVersion {self.document_id} v{self.version_number}>"


class DocumentChange(Base):
    """Individual changes within a document version."""
    __tablename__ = "document_changes"
    
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False)
    
    # Change details
    change_type = Column(String(20), nullable=False)  # line_added, line_deleted, line_modified
    line_number = Column(Integer, nullable=True)
    old_content = Column(Text, nullable=True)
    new_content = Column(Text, nullable=True)
    
    # Context
    function_name = Column(String(200), nullable=True)  # Function/method containing change
    class_name = Column(String(200), nullable=True)   # Class containing change
    section_type = Column(String(50), nullable=True)   # imports, function, class, etc.
    
    # Semantic information
    change_category = Column(String(50), nullable=True)  # bug_fix, feature, refactor, etc.
    impact_score = Column(Integer, default=1)  # 1-5 scale of change impact
    
    # Relationships
    version = relationship("DocumentVersion", back_populates="changes")
    
    def __repr__(self):
        return f"<DocumentChange {self.change_type} line {self.line_number}>"


class DocumentSnapshot(Base):
    """Full content snapshots for major versions."""
    __tablename__ = "document_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("code_documents.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False)
    
    # Content
    full_content = Column(Text, nullable=False)
    content_encoding = Column(String(20), default="utf-8")
    
    # Metadata
    snapshot_type = Column(String(20), nullable=False)  # major, backup, milestone
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    document = relationship("CodeDocument")
    version = relationship("DocumentVersion")
    
    def __repr__(self):
        return f"<DocumentSnapshot {self.document_id} v{self.version_id}>"


class ChangeBaseline(Base):
    """Baseline points for calculating diffs efficiently."""
    __tablename__ = "change_baselines"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("code_documents.id"), nullable=False)
    
    # Baseline information
    baseline_version = Column(Integer, nullable=False)
    baseline_hash = Column(String(64), nullable=False)
    baseline_timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Performance optimization
    total_versions = Column(Integer, default=0)
    total_changes = Column(Integer, default=0)
    
    # Relationships
    document = relationship("CodeDocument")
    
    def __repr__(self):
        return f"<ChangeBaseline {self.document_id} v{self.baseline_version}>"