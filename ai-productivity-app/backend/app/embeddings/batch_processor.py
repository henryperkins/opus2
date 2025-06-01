# backend/app/embeddings/batch_processor.py
"""Batch processing for embedding generation with progress tracking."""
from typing import List, Optional, Dict, Any
import asyncio
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.code import CodeDocument, CodeEmbedding
from app.embeddings.generator import EmbeddingGenerator

logger = logging.getLogger(__name__)


class BatchEmbeddingProcessor:
    """Process embeddings in batches with progress tracking."""

    def __init__(self, generator: EmbeddingGenerator):
        self.generator = generator
        self.batch_size = 100  # Process 100 chunks at a time
        self.progress_callbacks = []

    def add_progress_callback(self, callback):
        """Add callback for progress updates."""
        self.progress_callbacks.append(callback)

    async def _report_progress(
        self, processed: int, total: int, status: str = "processing"
    ):
        """Report progress to callbacks."""
        progress = {
            "processed": processed,
            "total": total,
            "percentage": (processed / total * 100) if total > 0 else 0,
            "status": status,
        }

        for callback in self.progress_callbacks:
            try:
                await callback(progress)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")

    async def process_project_embeddings(
        self, project_id: int, db: Session, force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """Generate all embeddings for a project."""
        # Get all chunks for the project
        query = (
            db.query(CodeEmbedding)
            .join(CodeDocument)
            .filter(CodeDocument.project_id == project_id)
        )

        if not force_regenerate:
            # Only process chunks without embeddings
            query = query.filter(CodeEmbedding.embedding.is_(None))

        chunks = query.all()

        if not chunks:
            return {"status": "no_chunks_to_process", "processed": 0, "total": 0}

        total = len(chunks)
        processed = 0
        failed = 0

        # Report initial progress
        await self._report_progress(0, total, "starting")

        # Process in batches
        for i in range(0, total, self.batch_size):
            batch = chunks[i : i + self.batch_size]

            try:
                await self.generator.generate_and_store(batch, db)
                processed += len(batch)

                # Report progress
                await self._report_progress(processed, total)

                # Small delay to avoid rate limits
                if processed < total:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                failed += len(batch)

                # Continue with next batch
                continue

        # Final progress report
        status = "completed" if failed == 0 else "completed_with_errors"
        await self._report_progress(processed, total, status)

        return {
            "status": status,
            "processed": processed,
            "failed": failed,
            "total": total,
        }

    async def process_document_embeddings(
        self, document_id: int, db: Session
    ) -> Dict[str, Any]:
        """Generate embeddings for a single document."""
        # Get all chunks for the document
        chunks = (
            db.query(CodeEmbedding)
            .filter(
                CodeEmbedding.document_id == document_id,
                CodeEmbedding.embedding.is_(None),
            )
            .all()
        )

        if not chunks:
            return {"status": "no_chunks_to_process", "processed": 0, "total": 0}

        try:
            await self.generator.generate_and_store(chunks, db)

            return {
                "status": "completed",
                "processed": len(chunks),
                "total": len(chunks),
            }
        except Exception as e:
            logger.error(f"Document embedding generation failed: {e}")
            return {
                "status": "failed",
                "processed": 0,
                "total": len(chunks),
                "error": str(e),
            }

    async def estimate_processing_time(self, chunk_count: int) -> float:
        """Estimate processing time in seconds."""
        # Rough estimate: 0.1 seconds per chunk + API overhead
        api_time = chunk_count * 0.1
        overhead = (chunk_count / self.batch_size) * 2  # 2 seconds overhead per batch

        return api_time + overhead
