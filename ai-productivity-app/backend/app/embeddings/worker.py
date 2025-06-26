"""Async embedding worker loop for continuous embedding generation.

This worker continuously processes CodeEmbedding records that don't have
embeddings yet, generates embeddings via the EmbeddingGenerator, and
stores them in both the database and Qdrant vector store.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

# Optional Prometheus metrics
try:
    from prometheus_client import Gauge
    EMBEDDING_QUEUE = Gauge("embedding_queue_length", "Pending embeddings count")
    HAS_PROMETHEUS = True
except ImportError:
    EMBEDDING_QUEUE = None
    HAS_PROMETHEUS = False

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import settings
from app.embeddings.generator import EmbeddingGenerator
from app.models.code import CodeDocument, CodeEmbedding
from app.services.vector_service import get_vector_service, VectorService

logger = logging.getLogger(__name__)


class EmbeddingWorker:
    """Background worker for continuous embedding generation."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        generator: Optional[EmbeddingGenerator] = None,
        vector_store: Optional[VectorService] = None,
    ):
        self.session_maker = session_maker
        self.generator = generator or EmbeddingGenerator()
        self.vector_store = vector_store
        self.running = False
        self._task: Optional[asyncio.Task] = None

        # Retry delays in seconds
        self.retry_delays = (1, 5, 30, 120)

    async def start(self) -> None:
        """Start the background worker loop."""
        if self.running:
            logger.warning("Embedding worker is already running")
            return

        # Initialize vector service if not provided
        if self.vector_store is None:
            from app.services.vector_service import vector_service
            self.vector_store = vector_service
            await self.vector_store.initialize()

        self.running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("Embedding worker started")

    async def stop(self) -> None:
        """Stop the background worker loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Embedding worker stopped")

    async def _worker_loop(self) -> None:
        """Main worker loop that processes embeddings."""
        consecutive_errors = 0
        last_gc_time = 0

        while self.running:
            try:
                processed = await self._process_batch()

                if processed > 0:
                    logger.info("Processed %d embeddings", processed)
                    consecutive_errors = 0
                else:
                    # No work to do, sleep for a bit
                    await asyncio.sleep(5)
                    consecutive_errors = 0

                # Run garbage collection once per hour (only for backends that support it)
                import time
                current_time = time.time()
                if current_time - last_gc_time > 3600:  # 1 hour
                    try:
                        logger.info("Running vector store garbage collection")
                        # Only run GC if the backend supports it
                        backend = await self.vector_store._get_backend()
                        if hasattr(backend, 'gc_dangling_points'):
                            removed = await backend.gc_dangling_points()
                            logger.info("GC completed: removed %s dangling points", removed)
                        else:
                            logger.info("Vector store backend doesn't support garbage collection")
                        last_gc_time = current_time
                    except Exception as gc_exc:
                        logger.warning("Vector store GC failed: %s", gc_exc)

            except Exception:
                logger.exception("Error in embedding worker loop")
                consecutive_errors += 1

                # Exponential backoff based on consecutive errors
                delay_index = min(consecutive_errors - 1, len(self.retry_delays) - 1)
                delay = self.retry_delays[delay_index]

                logger.warning(
                    "Backing off for %d seconds after %d consecutive errors",
                    delay, consecutive_errors
                )
                await asyncio.sleep(delay)

    async def _process_batch(self) -> int:
        """Process a batch of embeddings. Returns number processed."""
        async with self.session_maker() as db:
            # Find embeddings that need to be generated
            stmt = (
                select(CodeEmbedding)
                .where(CodeEmbedding.embedding.is_(None))
                .limit(100)
                .options(
                    # Eagerly load the document relationship
                    selectinload(CodeEmbedding.document)
                )
            )

            result = await db.execute(stmt)
            chunks = result.scalars().all()

            if not chunks:
                return 0

            logger.info("Found %d chunks needing embeddings", len(chunks))

            # Update queue metrics
            if HAS_PROMETHEUS and EMBEDDING_QUEUE:
                EMBEDDING_QUEUE.set(len(chunks))

            try:
                # Generate embeddings
                await self.generator.generate_and_store(chunks, db, vector_store=self.vector_store)

                # Store in vector store
                await self._store_in_vector_store(chunks)

                # Mark parent documents as indexed when all chunks are ready
                await self._update_document_index_status(db, chunks)

                await db.commit()
                return len(chunks)

            except Exception:
                logger.exception("Failed to process embedding batch")
                await db.rollback()
                raise

    async def _store_in_vector_store(self, chunks: list[CodeEmbedding]) -> None:
        """Store embeddings in the configured vector store."""
        embeddings_to_insert = []

        for chunk in chunks:
            if not chunk.embedding:
                continue

            embedding_data = {
                "id": chunk.id,  # Add required ID field for Qdrant
                "vector": chunk.embedding,
                "document_id": chunk.document_id,
                "project_id": chunk.document.project_id,
                "chunk_id": chunk.id,
                "content": chunk.chunk_content,
                "content_hash": "",  # Add if needed
                "metadata": {
                    "file_path": chunk.document.file_path,
                    "language": chunk.document.language,
                    "symbol_name": chunk.symbol_name,
                    "symbol_type": chunk.symbol_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                }
            }
            embeddings_to_insert.append(embedding_data)

        if embeddings_to_insert:
            await self.vector_store.insert_embeddings(embeddings_to_insert)

    async def _update_document_index_status(
        self, db: AsyncSession, chunks: list[CodeEmbedding]
    ) -> None:
        """Mark documents as indexed when all their chunks have embeddings."""
        doc_ids = {chunk.document_id for chunk in chunks}

        for doc_id in doc_ids:
            # Check if all chunks for this document have embeddings
            stmt = (
                select(CodeEmbedding)
                .where(CodeEmbedding.document_id == doc_id)
                .where(CodeEmbedding.embedding.is_(None))
            )
            result = await db.execute(stmt)
            unprocessed = result.scalars().first()

            if not unprocessed:
                # All chunks have embeddings, mark document as indexed
                doc_stmt = select(CodeDocument).where(CodeDocument.id == doc_id)
                doc_result = await db.execute(doc_stmt)
                doc = doc_result.scalar_one_or_none()

                if doc and not doc.is_indexed:
                    doc.is_indexed = True
                    logger.info("Marked document %d as indexed", doc_id)


# Global worker instance
_worker: Optional[EmbeddingWorker] = None


def start_background_loop() -> None:
    """Start the global embedding worker background loop.

    This function is called during application startup to begin
    processing embeddings in the background.
    """
    global _worker

    if _worker is not None:
        logger.warning("Embedding worker already initialized")
        return

    # -------------------------------------------------------------------
    # Create async engine – reuse central helper to ensure the generated URL
    # is compatible with *asyncpg* (strip unsupported query params like
    # ``sslmode``).
    # -------------------------------------------------------------------

    from app.database import _build_async_db_url  # local import to avoid cycle

    async_db_url = _build_async_db_url(settings.database_url)

    connect_args: dict[str, object] = {}
    if async_db_url.startswith("postgresql+asyncpg"):
        # Ensure SSL is used when connecting to Neon / Cloud Postgres.
        connect_args["ssl"] = True

    engine = create_async_engine(
        async_db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        connect_args=connect_args,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    # Initialize worker
    _worker = EmbeddingWorker(session_maker)

    # Start the worker loop
    asyncio.create_task(_worker.start())
    logger.info("Embedding worker background loop started")


async def stop_background_loop() -> None:
    """Stop the global embedding worker background loop.

    This function is called during application shutdown.
    """
    global _worker

    if _worker is not None:
        await _worker.stop()
        _worker = None
