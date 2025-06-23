# backend/app/embeddings/generator.py
"""OpenAI embedding generation with batching and error handling."""
import functools
import logging
from typing import List, Dict

# Sentry is optional in dev/CI. Use same stub fallback as llm.client.
try:
    import sentry_sdk  # type: ignore  # pragma: no cover
except ModuleNotFoundError:  # pragma: no cover

    class _StubSentry:  # pylint: disable=too-few-public-methods
        @staticmethod
        def capture_exception(_exc):
            return None

    sentry_sdk = _StubSentry()  # type: ignore
from openai import (
    RateLimitError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    AsyncOpenAI,
    AsyncAzureOpenAI
)
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import (
    EmbeddingException,
    VectorDimensionMismatchException
)
from app.models.code import CodeEmbedding

# ``tenacity`` is only required for automatic retries when the real embedding
# generation runs. We fall back to a *no-op* implementation when the dependency
# is missing so that the broader application remains usable in minimal
# environments.

try:
    from tenacity import (  # type: ignore
        retry,
        stop_after_attempt,
        wait_exponential
    )
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    def retry(*dargs, **_dkwargs):
        """No-op retry decorator when *tenacity* is unavailable."""

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                """Wrapper for retry decorator fallback."""
                return await func(*args, **kwargs)

            return wrapper

        # If used as @retry without (), dargs[0] is the function
        if dargs and callable(dargs[0]):
            return decorator(dargs[0])

        return decorator

    def stop_after_attempt(_):
        """Dummy stop after attempt when tenacity unavailable."""
        return None

    def wait_exponential(**_):
        """Dummy wait exponential when tenacity unavailable."""
        return None
try:
    from azure.identity import (
        DefaultAzureCredential,
        get_bearer_token_provider
    )
    HAS_AZURE_IDENTITY = True
except ImportError:
    HAS_AZURE_IDENTITY = False
    DefaultAzureCredential = None
    get_bearer_token_provider = None

# The OpenAI python package provides dedicated *Async* client-classes for the
# public OpenAI as well as the Azure OpenAI endpoints. Selecting the correct
# implementation ensures we use the right authentication- & endpoint
# parameters while keeping the rest of the code-base provider agnostic.

# OpenAI client classes are imported above with other openai imports

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using OpenAI API with batching."""

    def __init__(self, model: str = "text-embedding-3-small"):
        # The *model* parameter means **deployment** for Azure and **model
        # family** for public OpenAI.  We therefore accept either a plain
        # model name ("text-embedding-3-small") **or** a dict-like string of
        # the form ``deployment_name:model`` where the right part is used for
        # dimension validation.

        if ":" in model:
            self.deployment_name, self.model = model.split(":", 1)
        else:
            self.deployment_name, self.model = model, model
        self.client = None
        self.batch_size = 50  # OpenAI limit
        self._init_client()

    def _init_client(self):
        """Create *AsyncOpenAI* or *AsyncAzureOpenAI* client instance.

        The application supports two *providers* configured via the
        ``LLM_PROVIDER`` / ``llm_provider`` setting:

        • "openai" – regular public OpenAI endpoint
        • "azure"  – Azure OpenAI service (different host + auth headers)
        """

        provider = settings.llm_provider.lower()

        if provider == "azure":
            if not settings.azure_openai_endpoint:
                logger.warning(
                    "Azure OpenAI chosen but 'AZURE_OPENAI_ENDPOINT' missing"
                )
                return

            # Auth strategy configuration
            auth_method = getattr(
                settings, "azure_auth_method", "api_key"
            ).lower()

            extra_kwargs: Dict[str, str] = {
                "azure_endpoint": settings.azure_openai_endpoint,
                "api_version": getattr(
                    settings, "azure_openai_api_version", "2024-02-01"
                ),
            }

            try:
                if auth_method == "entra_id":
                    if not HAS_AZURE_IDENTITY:
                        raise RuntimeError(
                            "azure-identity package not available"
                        )

                    token_provider = get_bearer_token_provider(
                        DefaultAzureCredential(),
                        "https://cognitiveservices.azure.com/.default",
                    )
                    extra_kwargs[
                        "azure_ad_token_provider"
                    ] = token_provider
                else:  # default to API key
                    if not settings.azure_openai_api_key:
                        raise RuntimeError(
                            "'AZURE_OPENAI_API_KEY' not configured"
                        )
                    extra_kwargs["api_key"] = settings.azure_openai_api_key

                self.client = AsyncAzureOpenAI(**extra_kwargs)

            except (RuntimeError, ValueError, TypeError) as exc:
                logger.error(
                    "Failed to initialise Azure OpenAI client: %s", exc
                )
                self.client = None
        else:  # public OpenAI
            if not settings.openai_api_key:
                logger.warning(
                    "OpenAI API key not configured – embeddings disabled"
                )
                return

            try:
                self.client = AsyncOpenAI(
                    api_key=settings.openai_api_key
                )
            except (ValueError, TypeError, RuntimeError) as exc:
                logger.error("Failed to initialise OpenAI client: %s", exc)
                self.client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=(RateLimitError, APITimeoutError),
        reraise=True,
    )
    async def generate_embeddings(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings with specific error handling."""
        if not self.client:
            raise EmbeddingException(
                "Embedding client not initialized",
                error_code="CLIENT_NOT_INITIALIZED"
            )

        if not texts:
            return []

        # Validate input size
        total_tokens = sum(self.estimate_tokens(t) for t in texts)
        if total_tokens > 8000:  # Model limit
            raise EmbeddingException(
                f"Input too large: {total_tokens} tokens (max 8000)",
                error_code="INPUT_TOO_LARGE",
                details={
                    "total_tokens": total_tokens,
                    "max_tokens": 8000
                }
            )

        try:
            embeddings = []

            # Process in batches
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]

                response = await self.client.embeddings.create(
                    model=self.deployment_name,
                    input=batch
                )

                for item in response.data:
                    embedding = item.embedding

                    # Validate dimension
                    if not self.validate_dimension(embedding):
                        expected = self._get_expected_dimension()
                        raise VectorDimensionMismatchException(
                            expected, len(embedding)
                        )

                    embeddings.append(embedding)

            logger.info("Generated %d embeddings", len(embeddings))
            return embeddings

        except (AuthenticationError, BadRequestError) as e:
            logger.error("Embedding generation failed: %s", e)
            raise EmbeddingException(
                f"Failed to generate embeddings: {e}",
                error_code="GENERATION_FAILED"
            ) from e

        except RateLimitError as e:
            # Re-raise for retry decorator
            logger.warning("Embedding rate limit: %s", e)
            raise

        except APITimeoutError as e:
            # Re-raise for retry decorator
            logger.warning("Embedding timeout: %s", e)
            raise

        except Exception as e:
            logger.error(
                "Unexpected embedding error: %s", e, exc_info=True
            )
            sentry_sdk.capture_exception(e)
            raise EmbeddingException(
                "Unexpected error during embedding generation",
                error_code="UNKNOWN_ERROR"
            ) from e

    async def generate_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else []

    async def generate_and_store(
        self, chunks: List["CodeEmbedding"], db: "Session"
    ):
        """Generate embeddings for code chunks and update database."""
        if not chunks:
            return

        # Prepare texts with context
        texts = []
        for chunk in chunks:
            # Format text with metadata for better embeddings
            context = f"Language: {chunk.document.language}\n"
            if chunk.symbol_type and chunk.symbol_name:
                context += (
                    f"{chunk.symbol_type} {chunk.symbol_name}\n"
                )
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
                doc = (
                    db.query("CodeDocument")
                    .filter_by(id=doc_id)
                    .first()
                )
                if doc:
                    doc.is_indexed = True

            db.commit()

            logger.info(
                "Generated and stored %d embeddings", len(embeddings)
            )

        except (EmbeddingException, VectorDimensionMismatchException) as e:
            logger.error("Failed to generate embeddings: %s", e)
            db.rollback()
            raise
        except Exception as e:
            logger.error("Unexpected error in generate_and_store: %s", e)
            db.rollback()
            sentry_sdk.capture_exception(e)
            raise EmbeddingException(
                "Unexpected error during embedding generation and storage",
                error_code="STORE_ERROR"
            ) from e

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text.

        Args:
            text: Input text to estimate tokens for

        Returns:
            Estimated token count (rough approximation)
        """
        # Rough estimate: 4 characters per token
        return len(text) // 4

    def validate_dimension(self, embedding: List[float]) -> bool:
        """Validate embedding dimension matches model.

        Args:
            embedding: The embedding vector to validate

        Returns:
            True if dimension matches expected model dimension
        """
        expected_dims = {
            # June-2025 reference dimensions
            "text-embedding-3-small": 1024,
            "text-embedding-3-large": 3072,
            # Legacy model still widely used
            "text-embedding-ada-002": 1536,
        }

        expected = expected_dims.get(self.model, 1536)
        return len(embedding) == expected

    def _get_expected_dimension(self) -> int:
        """Get expected embedding dimension for current model.

        Returns:
            Expected embedding dimension for the configured model
        """
        expected_dims = {
            "text-embedding-3-small": 1024,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return expected_dims.get(self.model, 1536)
