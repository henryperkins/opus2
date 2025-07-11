"""Document version control and change tracking service."""

import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from difflib import unified_diff, SequenceMatcher
import re

from sqlalchemy.orm import Session
from app.models.document_version import (
    DocumentVersion,
    DocumentChange,
    DocumentSnapshot,
    ChangeBaseline,
)
from app.models.code_document import CodeDocument
from app.core.database import get_db

logger = logging.getLogger(__name__)


class VersionControlService:
    """Service for tracking document versions and changes."""

    def __init__(self):
        self.max_versions_per_document = 100
        self.major_version_threshold = 10  # Create snapshot every 10 versions
        self.change_detection_threshold = 0.1  # 10% change for impact scoring

    async def create_version(
        self,
        db: Session,
        document_id: int,
        new_content: str,
        change_type: str = "modified",
        changed_by: str = "system",
        commit_hash: Optional[str] = None,
        branch_name: Optional[str] = None,
    ) -> DocumentVersion:
        """Create a new version of a document."""
        try:
            # Get current document
            document = (
                db.query(CodeDocument).filter(CodeDocument.id == document_id).first()
            )
            if not document:
                raise ValueError(f"Document {document_id} not found")

            # Calculate content hash
            content_hash = hashlib.sha256(new_content.encode()).hexdigest()

            # Get latest version
            latest_version = (
                db.query(DocumentVersion)
                .filter(DocumentVersion.document_id == document_id)
                .order_by(DocumentVersion.version_number.desc())
                .first()
            )

            version_number = (
                (latest_version.version_number + 1) if latest_version else 1
            )

            # Analyze changes
            old_content = document.content if document.content else ""
            changes_analysis = self._analyze_changes(old_content, new_content)

            # Create new version
            new_version = DocumentVersion(
                document_id=document_id,
                version_number=version_number,
                content_hash=content_hash,
                content_size=len(new_content),
                change_type=change_type,
                change_summary=changes_analysis["summary"],
                changed_by=changed_by,
                change_timestamp=datetime.utcnow(),
                lines_added=changes_analysis["lines_added"],
                lines_deleted=changes_analysis["lines_deleted"],
                lines_modified=changes_analysis["lines_modified"],
                commit_hash=commit_hash,
                branch_name=branch_name,
            )

            db.add(new_version)
            db.flush()  # Get the version ID

            # Create detailed change records
            await self._create_change_records(
                db, new_version.id, old_content, new_content
            )

            # Create snapshot if this is a major version
            if version_number % self.major_version_threshold == 0:
                await self._create_snapshot(
                    db, document_id, new_version.id, new_content
                )

            # Update document content
            document.content = new_content
            document.content_hash = content_hash
            document.updated_at = datetime.utcnow()

            # Cleanup old versions if necessary
            await self._cleanup_old_versions(db, document_id)

            db.commit()
            logger.info(f"Created version {version_number} for document {document_id}")

            return new_version

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create version: {e}")
            raise

    def _analyze_changes(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """Analyze changes between two versions of content."""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        # Calculate line-level changes
        matcher = SequenceMatcher(None, old_lines, new_lines)
        changes = {
            "lines_added": 0,
            "lines_deleted": 0,
            "lines_modified": 0,
            "summary": "",
        }

        for op, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            if op == "insert":
                changes["lines_added"] += new_end - new_start
            elif op == "delete":
                changes["lines_deleted"] += old_end - old_start
            elif op == "replace":
                changes["lines_modified"] += max(
                    old_end - old_start, new_end - new_start
                )

        # Generate summary
        total_changes = (
            changes["lines_added"]
            + changes["lines_deleted"]
            + changes["lines_modified"]
        )
        if total_changes == 0:
            changes["summary"] = "No changes"
        elif total_changes < 5:
            changes["summary"] = "Minor changes"
        elif total_changes < 20:
            changes["summary"] = "Moderate changes"
        else:
            changes["summary"] = "Major changes"

        return changes

    async def _create_change_records(
        self, db: Session, version_id: int, old_content: str, new_content: str
    ):
        """Create detailed change records for a version."""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        matcher = SequenceMatcher(None, old_lines, new_lines)

        for op, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            if op == "equal":
                continue

            # Determine change type and content
            if op == "insert":
                for i in range(new_start, new_end):
                    change = DocumentChange(
                        version_id=version_id,
                        change_type="line_added",
                        line_number=i + 1,
                        new_content=new_lines[i] if i < len(new_lines) else "",
                        impact_score=self._calculate_impact_score(
                            new_lines[i] if i < len(new_lines) else ""
                        ),
                    )
                    db.add(change)

            elif op == "delete":
                for i in range(old_start, old_end):
                    change = DocumentChange(
                        version_id=version_id,
                        change_type="line_deleted",
                        line_number=i + 1,
                        old_content=old_lines[i] if i < len(old_lines) else "",
                        impact_score=self._calculate_impact_score(
                            old_lines[i] if i < len(old_lines) else ""
                        ),
                    )
                    db.add(change)

            elif op == "replace":
                # Handle line modifications
                for i in range(max(old_end - old_start, new_end - new_start)):
                    old_line = (
                        old_lines[old_start + i] if old_start + i < old_end else ""
                    )
                    new_line = (
                        new_lines[new_start + i] if new_start + i < new_end else ""
                    )

                    change = DocumentChange(
                        version_id=version_id,
                        change_type="line_modified",
                        line_number=old_start + i + 1,
                        old_content=old_line,
                        new_content=new_line,
                        impact_score=max(
                            self._calculate_impact_score(old_line),
                            self._calculate_impact_score(new_line),
                        ),
                    )
                    db.add(change)

    def _calculate_impact_score(self, line: str) -> int:
        """Calculate the impact score of a line change (1-5 scale)."""
        line = line.strip()

        # High impact patterns
        if any(
            pattern in line.lower()
            for pattern in [
                "def ",
                "class ",
                "import ",
                "from ",
                "return",
                "raise",
                "except",
            ]
        ):
            return 5

        # Medium-high impact
        if any(
            pattern in line.lower()
            for pattern in [
                "if ",
                "elif ",
                "else:",
                "for ",
                "while ",
                "try:",
                "finally:",
            ]
        ):
            return 4

        # Medium impact
        if any(
            pattern in line.lower()
            for pattern in ["=", "+=", "-=", "*=", "/=", "==", "!=", "<=", ">="]
        ):
            return 3

        # Low impact
        if line.startswith("#") or line.startswith('"""') or line.startswith("'''"):
            return 1

        # Default medium-low impact
        return 2

    async def _create_snapshot(
        self,
        db: Session,
        document_id: int,
        version_id: int,
        content: str,
        snapshot_type: str = "major",
    ):
        """Create a full content snapshot."""
        snapshot = DocumentSnapshot(
            document_id=document_id,
            version_id=version_id,
            full_content=content,
            snapshot_type=snapshot_type,
            created_at=datetime.utcnow(),
        )
        db.add(snapshot)

    async def _cleanup_old_versions(self, db: Session, document_id: int):
        """Clean up old versions to stay within limits."""
        versions = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
            .all()
        )

        if len(versions) > self.max_versions_per_document:
            # Keep major versions and recent versions
            versions_to_delete = []
            for version in versions[self.max_versions_per_document :]:
                # Keep major versions (with snapshots)
                has_snapshot = (
                    db.query(DocumentSnapshot)
                    .filter(DocumentSnapshot.version_id == version.id)
                    .first()
                )

                if not has_snapshot:
                    versions_to_delete.append(version)

            # Delete old versions and their changes
            for version in versions_to_delete:
                db.query(DocumentChange).filter(
                    DocumentChange.version_id == version.id
                ).delete()
                db.delete(version)

    async def get_version_history(
        self,
        db: Session,
        document_id: int,
        limit: int = 50,
        include_changes: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get version history for a document."""
        versions = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(limit)
            .all()
        )

        history = []
        for version in versions:
            version_data = {
                "id": version.id,
                "version_number": version.version_number,
                "change_type": version.change_type,
                "change_summary": version.change_summary,
                "changed_by": version.changed_by,
                "change_timestamp": version.change_timestamp,
                "lines_added": version.lines_added,
                "lines_deleted": version.lines_deleted,
                "lines_modified": version.lines_modified,
                "commit_hash": version.commit_hash,
                "branch_name": version.branch_name,
            }

            if include_changes:
                changes = (
                    db.query(DocumentChange)
                    .filter(DocumentChange.version_id == version.id)
                    .all()
                )
                version_data["changes"] = [
                    {
                        "change_type": change.change_type,
                        "line_number": change.line_number,
                        "old_content": change.old_content,
                        "new_content": change.new_content,
                        "impact_score": change.impact_score,
                    }
                    for change in changes
                ]

            history.append(version_data)

        return history

    async def get_version_diff(
        self, db: Session, document_id: int, from_version: int, to_version: int
    ) -> Dict[str, Any]:
        """Get diff between two versions."""
        from_ver = (
            db.query(DocumentVersion)
            .filter(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version_number == from_version,
            )
            .first()
        )

        to_ver = (
            db.query(DocumentVersion)
            .filter(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version_number == to_version,
            )
            .first()
        )

        if not from_ver or not to_ver:
            raise ValueError("Version not found")

        # Get content for both versions
        from_content = await self._get_version_content(db, from_ver.id)
        to_content = await self._get_version_content(db, to_ver.id)

        # Generate diff
        diff_lines = list(
            unified_diff(
                from_content.splitlines(),
                to_content.splitlines(),
                fromfile=f"Version {from_version}",
                tofile=f"Version {to_version}",
                lineterm="",
            )
        )

        return {
            "from_version": from_version,
            "to_version": to_version,
            "diff": "\n".join(diff_lines),
            "changes_summary": {
                "versions_compared": abs(to_version - from_version),
                "from_timestamp": from_ver.change_timestamp,
                "to_timestamp": to_ver.change_timestamp,
            },
        }

    async def _get_version_content(self, db: Session, version_id: int) -> str:
        """Get content for a specific version."""
        # First try to get from snapshot
        snapshot = (
            db.query(DocumentSnapshot)
            .filter(DocumentSnapshot.version_id == version_id)
            .first()
        )

        if snapshot:
            return snapshot.full_content

        # Otherwise, reconstruct from changes (simplified for now)
        version = (
            db.query(DocumentVersion).filter(DocumentVersion.id == version_id).first()
        )

        if not version:
            raise ValueError(f"Version {version_id} not found")

        # Get current document content as fallback
        document = (
            db.query(CodeDocument)
            .filter(CodeDocument.id == version.document_id)
            .first()
        )

        return document.content if document else ""

    async def restore_version(
        self,
        db: Session,
        document_id: int,
        target_version: int,
        restored_by: str = "system",
    ) -> DocumentVersion:
        """Restore a document to a previous version."""
        # Get target version
        target_ver = (
            db.query(DocumentVersion)
            .filter(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version_number == target_version,
            )
            .first()
        )

        if not target_ver:
            raise ValueError(f"Version {target_version} not found")

        # Get content for target version
        target_content = await self._get_version_content(db, target_ver.id)

        # Create new version with restored content
        new_version = await self.create_version(
            db=db,
            document_id=document_id,
            new_content=target_content,
            change_type="restored",
            changed_by=restored_by,
        )

        return new_version


# Global instance
version_control_service = VersionControlService()
