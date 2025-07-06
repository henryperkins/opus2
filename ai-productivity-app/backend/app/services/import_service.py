# backend/app/services/import_service.py
"""Enhanced import service with atomic operations."""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.models.import_job import ImportJob, ImportStatus
from app.models.code import CodeDocument
from app.database.transactions import TransactionManager
import logging

logger = logging.getLogger(__name__)


class AtomicImportService:
    """Import operations with transaction safety."""

    @staticmethod
    async def update_import_status(
        db: Session,
        job_id: int,
        status: ImportStatus,
        progress: int,
        error: Optional[str] = None
    ) -> bool:
        """Update import job status atomically."""
        tm = TransactionManager(db)

        async with tm.atomic():
            job = db.query(ImportJob).filter_by(id=job_id).first()
            if not job:
                return False

            job.status = status
            job.progress_pct = progress
            if error:
                job.error = error

            # Touch to update timestamp
            job.touch()

            # Log status change
            logger.info(
                "Import job %s status: %s -> %s (progress: %d%%)",
                job_id, job.status, status, progress
            )

            return True

    @staticmethod
    async def create_documents_batch(
        db: Session,
        project_id: int,
        files: list[dict]
    ) -> list[CodeDocument]:
        """Create multiple code documents in single transaction."""
        tm = TransactionManager(db)
        documents = []

        async with tm.atomic():
            for file_info in files:
                doc = CodeDocument(
                    project_id=project_id,
                    file_path=file_info['path'],
                    language=file_info.get('language'),
                    content_hash=file_info['hash'],
                    file_size=file_info.get('size', 0),
                    is_indexed=False  # Mark as not indexed until embeddings are complete
                )
                db.add(doc)
                documents.append(doc)

            # Flush to get IDs
            db.flush()

            logger.info(
                "Created %d code documents for project %d",
                len(documents), project_id
            )

        return documents

    @staticmethod
    async def update_changed_documents(
        db: Session,
        project_id: int,
        changed_files: list[dict],
        deleted_files: list[str]
    ) -> dict:
        """Update only changed files for incremental indexing."""
        tm = TransactionManager(db)
        results = {"updated": 0, "created": 0, "deleted": 0}

        async with tm.atomic():
            # Handle deleted files
            if deleted_files:
                delete_stmt = delete(CodeDocument).where(
                    CodeDocument.project_id == project_id,
                    CodeDocument.file_path.in_(deleted_files)
                )
                deleted_result = db.execute(delete_stmt)
                results["deleted"] = deleted_result.rowcount

            # Handle changed/new files
            for file_info in changed_files:
                select_stmt = select(CodeDocument).where(
                    CodeDocument.project_id == project_id,
                    CodeDocument.file_path == file_info['path']
                )
                result = db.execute(select_stmt)
                doc = result.scalar_one_or_none()
                
                if doc:
                    # Update existing document
                    doc.content_hash = file_info['hash']
                    doc.file_size = file_info.get('size', 0)
                    doc.language = file_info.get('language')
                    doc.is_indexed = False  # Mark for re-indexing
                    results["updated"] += 1
                else:
                    # Create new document
                    new_doc = CodeDocument(
                        project_id=project_id,
                        file_path=file_info['path'],
                        language=file_info.get('language'),
                        content_hash=file_info['hash'],
                        file_size=file_info.get('size', 0),
                        is_indexed=False
                    )
                    db.add(new_doc)
                    results["created"] += 1

            logger.info(
                "Incremental update for project %d: %d updated, %d created, %d deleted",
                project_id, results["updated"], results["created"], results["deleted"]
            )

        return results
