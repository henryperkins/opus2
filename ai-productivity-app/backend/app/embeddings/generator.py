# backend/app/embeddings/generator.py
"""OpenAI embedding generation with batching and error handling."""
import openai
from typing import List, Dict, Optional
# ``numpy`` is only needed when the embedding functionality is exercised.  We
# import it lazily so that the rest of the application (and lightweight test
# suites) continue to work in environments where the dependency is absent.

try:
    import numpy as np  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    np = None  # type: ignore
# ``tenacity`` is only required for automatic retries when the real embedding
# generation runs.  Similar to *numpy* we fall back to a *no-op* implementation
# when the dependency is missing so that the broader application remains usable
# in minimal environments.

try:
    from tenacity import retry, stop_after_attempt, wait_exponential  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    import functools

    def retry(*dargs, **dkwargs):  # noqa: D401 – simple wrapper
        """No-op retry decorator when *tenacity* is unavailable."""

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):  # pylint: disable=missing-docstring
                return await func(*args, **kwargs)

            return wrapper

        # If used as @retry without (), dargs[0] is the function
        if dargs and callable(dargs[0]):
            return decorator(dargs[0])

        return decorator

    # Dummy stop/ wait objects for signature compatibility
    def stop_after_attempt(_):  # noqa: D401
        return None

    def wait_exponential(**_):  # noqa: D401
        return None
import logging
import asyncio
from app.config import settings

# The OpenAI python package provides dedicated *Async* client-classes for the
# public OpenAI as well as the Azure OpenAI endpoints.  Selecting the correct
# implementation ensures we use the right authentication- & endpoint
# parameters while keeping the rest of the code-base provider agnostic.

try:
    from openai import AsyncOpenAI, AsyncAzureOpenAI
except ImportError:  # pragma: no cover – the dependency is declared in our
    # environment, therefore this should never happen in production.  We keep
    # a defensive fallback for unit-tests that monkey-patch the dependency.
    AsyncOpenAI = None  # type: ignore
    AsyncAzureOpenAI = None  # type: ignore

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using OpenAI API with batching."""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = None
        self.batch_size = 50  # OpenAI limit
        self._init_client()

    def _init_client(self):
        """Initialise the correct OpenAI client implementation.

        The application supports two *providers* configured via the
        ``LLM_PROVIDER`` / ``llm_provider`` setting:

        • "openai" – regular public OpenAI endpoint
        • "azure"  – Azure OpenAI service (different host + auth headers)
        """

        provider = settings.llm_provider.lower()

        if provider == "azure":
            if not (settings.azure_openai_api_key and settings.azure_openai_endpoint):
                logger.warning(
                    "Azure OpenAI selected as provider, but 'azure_openai_api_key' "
                    "or 'azure_openai_endpoint' is not configured."
                )
                return

            try:
                self.client = AsyncAzureOpenAI(
                    api_key=settings.azure_openai_api_key,
                    azure_endpoint=settings.azure_openai_endpoint,
                    # Default to the most recent stable API version if the user
                    # has not overridden it via an env-var.  The version *must*
                    # be supplied for Azure requests.
                    api_version=getattr(settings, "azure_openai_api_version", "2024-02-01"),
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to initialise Azure OpenAI client: %s", exc)
                self.client = None
        else:  # public OpenAI
            if not settings.openai_api_key:
                logger.warning("OpenAI API key not configured – embeddings disabled")
                return

            try:
                self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to initialise OpenAI client: %s", exc)
                self.client = None

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
