"""Async embedding worker loop for continuous embedding generation.

This worker continuously processes CodeEmbedding records that don't have
embeddings yet, generates embeddings via the EmbeddingGenerator, and
stores them in both the database and Qdrant vector store.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional


from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import settings
from app.embeddings.generator import EmbeddingGenerator, _is_oversize_error
from app.models.code import CodeDocument, CodeEmbedding
from app.services.vector_service import get_vector_service, VectorService
from app.monitoring.metrics import (
    record_oversize_error,
    record_retry_error,
    record_fatal_error,
    update_queue_length,
)

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

        # Retry delays in seconds (for transient errors only)
        self.retry_delays = (1, 5, 30, 120)

        # Circuit breaker state for oversized batch failures
        self.consecutive_oversize_failures = 0
        self.max_oversize_failures = 3
        self.circuit_breaker_delay = 300  # 5 minutes
        self.circuit_breaker_until = 0.0  # timestamp when circuit breaker expires

        # Adaptive batch sizing
        self.max_rows = settings.embedding_max_batch_rows
        self.min_rows = 1

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
        # DEBUG-level to avoid duplicating the info checkpoint emitted by
        # *start_background_loop()*.
        logger.debug("Embedding worker started")

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
                    # Don't reset consecutive_errors here - let circuit breaker handle it

                # Run garbage collection once per hour (only for backends that support it)
                current_time = time.time()
                if current_time - last_gc_time > 3600:  # 1 hour
                    try:
                        logger.info("Running vector store garbage collection")
                        # Only run GC if the backend supports it
                        backend = await self.vector_store.get_backend()
                        if hasattr(backend, "gc_dangling_points"):
                            removed = await backend.gc_dangling_points()
                            logger.info(
                                "GC completed: removed %s dangling points", removed
                            )
                        else:
                            logger.info(
                                "Vector store backend doesn't support garbage collection"
                            )
                        last_gc_time = current_time
                    except Exception as gc_exc:
                        logger.warning("Vector store GC failed: %s", gc_exc)

            except Exception as exc:
                logger.exception("Error in embedding worker loop")
                consecutive_errors += 1

                # Don't use exponential backoff for oversized errors (handled by circuit breaker)
                if _is_oversize_error(exc):
                    logger.info(
                        "Oversized error handled by circuit breaker, continuing immediately"
                    )
                    continue

                # Exponential backoff for other transient errors
                delay_index = min(consecutive_errors - 1, len(self.retry_delays) - 1)
                delay = self.retry_delays[delay_index]

                logger.warning(
                    "Backing off for %d seconds after %d consecutive errors",
                    delay,
                    consecutive_errors,
                )
                await asyncio.sleep(delay)

    async def _process_batch(self) -> int:
        """Process a batch of embeddings. Returns number processed."""
        # Check circuit breaker
        current_time = time.time()
        if current_time < self.circuit_breaker_until:
            logger.info(
                "Circuit breaker active for %.1f more seconds",
                self.circuit_breaker_until - current_time,
            )
            await asyncio.sleep(5)
            return 0

        async with self.session_maker() as db:
            # Adaptive batch sizing - reduce batch size if we've had oversized failures
            current_batch_size = max(
                self.min_rows, self.max_rows // (2**self.consecutive_oversize_failures)
            )

            # Find embeddings that need to be generated
            # Exclude chunks that have been marked as failed (empty embedding array)
            stmt = (
                select(CodeEmbedding)
                .where(CodeEmbedding.embedding.is_(None))
                .limit(current_batch_size)
                .options(
                    # Eagerly load the document relationship
                    selectinload(CodeEmbedding.document)
                )
            )

            result = await db.execute(stmt)
            chunks = result.scalars().all()

            if not chunks:
                # Reset consecutive failures when no work to do
                self.consecutive_oversize_failures = 0
                return 0

            logger.info(
                "Found %d chunks needing embeddings (batch size: %d, circuit breaker failures: %d)",
                len(chunks),
                current_batch_size,
                self.consecutive_oversize_failures,
            )

            # Update queue metrics
            update_queue_length(len(chunks))

            try:
                # Generate embeddings with token-aware batching
                await self.generator.generate_and_store(
                    chunks, db, vector_store=self.vector_store
                )

                # Store in vector store
                await self._store_in_vector_store(chunks)

                # Mark parent documents as indexed when all chunks are ready
                await self._update_document_index_status(db, chunks)

                await db.commit()

                # Reset circuit breaker on success
                self.consecutive_oversize_failures = 0
                return len(chunks)

            except Exception as exc:
                await db.rollback()

                # Handle oversized batch errors specially
                if _is_oversize_error(exc):
                    logger.error(
                        "Non-retryable oversized batch error: %s. "
                        "Marking %d chunks as failed to prevent retry loop",
                        exc,
                        len(chunks),
                    )

                    # Record metrics
                    total_tokens = sum(
                        self.generator.estimate_tokens(chunk.chunk_content)
                        for chunk in chunks
                    )
                    record_oversize_error(len(chunks), total_tokens)

                    # Update circuit breaker state
                    self.consecutive_oversize_failures += 1
                    if self.consecutive_oversize_failures >= self.max_oversize_failures:
                        self.circuit_breaker_until = (
                            current_time + self.circuit_breaker_delay
                        )
                        logger.error(
                            "Circuit breaker activated for %d seconds after %d consecutive oversized failures",
                            self.circuit_breaker_delay,
                            self.consecutive_oversize_failures,
                        )

                    # Mark chunks as failed to prevent re-queuing
                    await self._mark_chunks_failed(db, chunks, "oversized_batch")
                    await db.commit()
                    return 0

                # For other errors, record metrics and re-raise to trigger retry logic
                if (
                    "rate limit" in str(exc).lower()
                    or "RateLimitError" in type(exc).__name__
                ):
                    record_retry_error("rate_limit")
                elif (
                    "timeout" in str(exc).lower()
                    or "TimeoutError" in type(exc).__name__
                ):
                    record_retry_error("timeout")
                elif (
                    "auth" in str(exc).lower()
                    or "AuthenticationError" in type(exc).__name__
                ):
                    record_fatal_error("authentication")
                else:
                    record_retry_error("unknown")

                logger.exception("Failed to process embedding batch")
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
                },
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

    async def _mark_chunks_failed(
        self, db: AsyncSession, chunks: list[CodeEmbedding], reason: str
    ) -> None:
        """Mark chunks as failed to prevent infinite retry loops.

        This implementation marks chunks with a sentinel value to indicate
        failed processing, preventing them from being requeued.

        Args:
            db: Database session
            chunks: List of chunks to mark as failed
            reason: Reason for failure (for logging)
        """
        failed_chunk_ids = []

        for chunk in chunks:
            # Mark as failed with a sentinel value: empty list indicates failed processing
            chunk.embedding = []  # Empty list indicates failed processing
            chunk.embedding_dim = 0
            failed_chunk_ids.append(chunk.id)
            logger.warning(
                "Marked chunk %d (content length: %d chars) as failed due to: %s",
                chunk.id,
                len(chunk.chunk_content),
                reason,
            )

        # Optionally, update a separate failed_chunks table or add metadata
        # For now, we rely on the empty embedding list as the failure indicator
        logger.error(
            "Marked %d chunks as failed due to %s. Chunk IDs: %s",
            len(chunks),
            reason,
            failed_chunk_ids[:10],  # Log first 10 IDs
        )


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

    # Ensure the async driver is used: convert postgresql:// to postgresql+asyncpg:// if necessary.
    db_url = settings.database_url
    if db_url and db_url.startswith("postgresql://"):
        async_db_url = "postgresql+asyncpg://" + db_url[len("postgresql://") :]
    else:
        async_db_url = db_url

    # Remove asyncpg-incompatible parameters from URL
    if async_db_url and "?" in async_db_url:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(async_db_url)
        query_params = parse_qs(parsed.query)
        
        # Remove asyncpg-incompatible parameters
        incompatible_params = ['sslmode', 'channel_binding']
        for param in incompatible_params:
            query_params.pop(param, None)
        
        # Reconstruct URL with cleaned parameters
        new_query = urlencode(query_params, doseq=True)
        async_db_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

    connect_args: dict[str, object] = {}
    if async_db_url.startswith("postgresql+asyncpg"):
        # Ensure SSL is used when connecting to Neon / Cloud Postgres.
        connect_args["ssl"] = True

    engine = create_async_engine(
        async_db_url,
        echo=settings.debug_sql,
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
