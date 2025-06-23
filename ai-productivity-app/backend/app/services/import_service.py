# backend/app/services/import_service.py
"""Enhanced import service with atomic operations."""
from typing import Optional
from sqlalchemy.orm import Session
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
                    file_size=file_info.get('size', 0)
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
