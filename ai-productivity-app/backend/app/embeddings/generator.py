# backend/app/embeddings/generator.py
"""OpenAI embedding generation with batching and error handling."""
import openai
from typing import List, Dict, Optional
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using OpenAI API with batching."""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = None
        self.batch_size = 50  # OpenAI limit
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client."""
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured")
            return

        try:
            self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts with retry logic."""
        if not self.client:
            raise ValueError("OpenAI client not initialized")

        if not texts:
            return []

        embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]

            try:
                response = await self.client.embeddings.create(
                    model=self.model, input=batch
                )

                batch_embeddings = [e.embedding for e in response.data]
                embeddings.extend(batch_embeddings)

                # Log progress for large batches
                if len(texts) > self.batch_size:
                    logger.info(
                        f"Generated embeddings for {i + len(batch)}/{len(texts)} texts"
                    )

            except openai.RateLimitError as e:
                logger.warning(f"Rate limit hit: {e}")
                # Wait and retry
                await asyncio.sleep(60)
                raise
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                raise

        return embeddings

    async def generate_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else []

    async def generate_and_store(self, chunks: List["CodeEmbedding"], db: "Session"):
        """Generate embeddings for code chunks and update database."""
        if not chunks:
            return

        # Prepare texts with context
        texts = []
        for chunk in chunks:
            # Format text with metadata for better embeddings
            context = f"Language: {chunk.document.language}\n"
            if chunk.symbol_type and chunk.symbol_name:
                context += f"{chunk.symbol_type} {chunk.symbol_name}\n"
            context += f"File: {chunk.document.file_path}\n\n"
            context += chunk.chunk_content

            texts.append(context)

        # Generate embeddings
        try:
            embeddings = await self.generate_embeddings(texts)

            # Update chunks with embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding  # Will be stored as JSON
                chunk.embedding_dim = len(embedding)

            db.commit()

            # Update document as indexed
            doc_ids = set(chunk.document_id for chunk in chunks)
            for doc_id in doc_ids:
                doc = db.query("CodeDocument").filter_by(id=doc_id).first()
                if doc:
                    doc.is_indexed = True

            db.commit()

            logger.info(f"Generated and stored {len(embeddings)} embeddings")

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            db.rollback()
            raise

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text."""
        # Rough estimate: 4 characters per token
        return len(text) // 4

    def validate_dimension(self, embedding: List[float]) -> bool:
        """Validate embedding dimension matches model."""
        expected_dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

        expected = expected_dims.get(self.model, 1536)
        return len(embedding) == expected
