# backend/app/services/embedding_service.py
"""Service for managing embeddings lifecycle."""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import numpy as np
import hashlib
import logging

from app.models.code import CodeDocument, CodeEmbedding
from app.models.embedding import EmbeddingMetadata
from app.embeddings.generator import EmbeddingGenerator
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manage embedding generation and storage."""

    def __init__(
        self,
        db: Session,
        vector_store: VectorService,
        embedding_generator: EmbeddingGenerator,
    ):
        self.db = db
        self.vector_store = vector_store
        self.embedding_generator = embedding_generator
        self.batch_size = 50

    async def index_document(self, document_id: int) -> Dict:
        """Index all chunks for a document."""
        document = self.db.query(CodeDocument).filter_by(id=document_id).first()
        if not document:
            return {"status": "error", "message": "Document not found"}

        # Get chunks without embeddings
        chunks = (
            self.db.query(CodeEmbedding)
            .filter_by(document_id=document_id, embedding=None)
            .all()
        )

        if not chunks:
            return {"status": "success", "message": "No chunks to index", "indexed": 0}

        # Process in batches
        indexed = 0
        errors = 0

        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i : i + self.batch_size]

            try:
                await self._process_batch(document, batch)
                indexed += len(batch)
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                errors += len(batch)

        # Update document status
        document.is_indexed = indexed > 0
        self.db.commit()

        return {
            "status": "success" if errors == 0 else "partial",
            "indexed": indexed,
            "errors": errors,
            "total": len(chunks),
        }

    async def _process_batch(self, document: CodeDocument, chunks: List[CodeEmbedding]):
        """Process a batch of chunks."""
        # Prepare texts
        texts = []
        for chunk in chunks:
            # Add context for better embeddings
            context = f"Project: {document.project_id}\n"
            context += f"Language: {document.language}\n"
            context += f"File: {document.file_path}\n"

            if chunk.symbol_name:
                context += f"{chunk.symbol_type}: {chunk.symbol_name}\n"

            context += f"\n{chunk.chunk_content}"
            texts.append(context)

        # Generate embeddings
        embeddings = await self.embedding_generator.generate_embeddings(texts)

        # Prepare for vector store
        vector_data = []
        for chunk, embedding in zip(chunks, embeddings):
            # Store in chunk model
            chunk.embedding = embedding
            chunk.embedding_dim = len(embedding)

            # Prepare for vector store
            metadata = {
                "document_id": document.id,
                "chunk_id": chunk.id,
                "project_id": document.project_id,
                "content": chunk.chunk_content,
                "content_hash": hashlib.sha256(
                    chunk.chunk_content.encode()
                ).hexdigest(),
                "file_path": document.file_path,
                "language": document.language,
                "symbol_name": chunk.symbol_name,
                "symbol_type": chunk.symbol_type,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
            }

            vector_data.append({
                "id": chunk.id,  # Add required id field for Qdrant
                "vector": embedding,
                "document_id": document.id,
                "chunk_id": chunk.id,
                "project_id": document.project_id,
                "content": chunk.chunk_content,
                "content_hash": hashlib.sha256(
                    chunk.chunk_content.encode()
                ).hexdigest(),
                **metadata
            })

        # Insert into vector store
        await self.vector_store.insert_embeddings(vector_data)

        # Commit chunk updates
        self.db.commit()

    async def update_document_embeddings(self, document_id: int) -> Dict:
        """Update embeddings for changed chunks."""
        # Find chunks with outdated embeddings
        chunks = self.db.query(CodeEmbedding).filter_by(document_id=document_id).all()

        updated = 0
        for chunk in chunks:
            # Check if content changed
            current_hash = hashlib.sha256(chunk.chunk_content.encode()).hexdigest()

            # Get metadata
            metadata = (
                self.db.query(EmbeddingMetadata).filter_by(chunk_id=chunk.id).first()
            )

            if metadata and metadata.content_hash != current_hash:
                # Re-generate embedding
                context = f"Language: {chunk.document.language}\n"
                context += f"File: {chunk.document.file_path}\n"
                context += f"\n{chunk.chunk_content}"

                embedding = await self.embedding_generator.generate_single_embedding(
                    context
                )

                # Update vector store
                await self.vector_store.update_embedding(
                    metadata.rowid, np.array(embedding)
                )

                # Update metadata
                metadata.content = chunk.chunk_content
                metadata.content_hash = current_hash

                # Update chunk
                chunk.embedding = embedding

                updated += 1

        self.db.commit()

        return {"status": "success", "updated": updated, "total": len(chunks)}

    async def delete_document_embeddings(self, document_id: int):
        """Delete all embeddings for a document."""
        await self.vector_store.delete_by_document(document_id)

        # Clear embeddings in chunks
        self.db.query(CodeEmbedding).filter_by(document_id=document_id).update(
            {"embedding": None}
        )

        self.db.commit()
