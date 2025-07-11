# backend/app/embeddings/generator.py
"""Azure / OpenAI embedding generation with batching and modern features.

Key improvements over the previous revision
-------------------------------------------
1. Supports the new ``dimensions`` and ``encoding_format`` parameters that
   ship with the *text-embedding-3* model family (Azure preview 2025-04-01).
2. Central table with model metadata (dimension + token-limit) that is used
   for validation and cost estimation.
3. Optional base64 → float decoding when the caller asks for
   ``encoding_format="base64"`` so the rest of the application can keep using
   regular Python float vectors.
4. More fine-grained token-limit checks (per text & overall).
5. Slightly richer logging / metrics while staying dependency-light.
"""
from __future__ import annotations

import base64
import functools
import logging
import struct
import time
from typing import (
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
)

# --------------------------------------------------------------------------- #
# Optional runtime dependencies (sentry, tenacity, azure-identity)
# --------------------------------------------------------------------------- #
try:
    import sentry_sdk  # type: ignore  # pragma: no cover
except ModuleNotFoundError:  # pragma: no cover

    class _StubSentry:  # pylint: disable=too-few-public-methods
        @staticmethod
        def capture_exception(_exc):
            return None

    sentry_sdk = _StubSentry()  # type: ignore

try:
    from tenacity import (  # type: ignore
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        retry_if_exception,
    )
except ModuleNotFoundError:  # pragma: no cover

    def retry(*dargs, **_dkwargs):  # noqa: D401
        """No-op replacement when *tenacity* is unavailable."""

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):  # type: ignore[override]
                return await func(*args, **kwargs)

            return wrapper

        if dargs and callable(dargs[0]):  # used without ()
            return decorator(dargs[0])
        return decorator

    def stop_after_attempt(_):  # noqa: D401
        return None

    def wait_exponential(**_):  # noqa: D401
        return None

    def retry_if_exception_type(_):  # noqa: D401
        """Stub that always retries zero times (no-op)."""

        return None

    def retry_if_exception(_):  # noqa: D401
        """Stub that always retries zero times (no-op)."""

        return None

try:
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    HAS_AZURE_IDENTITY = True
except ImportError:
    HAS_AZURE_IDENTITY = False
    DefaultAzureCredential = None  # type: ignore
    get_bearer_token_provider = None  # type: ignore

# --------------------------------------------------------------------------- #
# Third-party OpenAI client
# --------------------------------------------------------------------------- #
from openai import (  # pylint: disable=wrong-import-position
    APITimeoutError,
    AsyncAzureOpenAI,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

# --------------------------------------------------------------------------- #
# First-party helpers
# --------------------------------------------------------------------------- #
from sqlalchemy.orm import Session  # pylint: disable=wrong-import-position
from sqlalchemy.ext.asyncio import AsyncSession  # pylint: disable=wrong-import-position

from app.config import settings  # pylint: disable=wrong-import-position
from app.exceptions import (  # pylint: disable=wrong-import-position
    EmbeddingException,
    VectorDimensionMismatchException,
)
from app.models.code import CodeEmbedding  # pylint: disable=wrong-import-position
from app.embeddings.cache import EMBEDDING_CACHE  # pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)


def _is_oversize_error(exc: Exception) -> bool:
    """Check if an exception represents an oversized batch error."""
    return (isinstance(exc, EmbeddingException) and
            ("Batch too large" in str(exc) or "INPUT_TOO_LARGE" in str(exc)))


def _is_retryable_error(exc: Exception) -> bool:
    """Check if an exception should be retried."""
    # Don't retry oversized batch errors - they're deterministic
    if _is_oversize_error(exc):
        return False

    # Retry rate limits and timeouts
    return isinstance(exc, (RateLimitError, APITimeoutError))


def _adaptive_wait(retry_state):
    """Custom wait function that respects Retry-After header from Azure OpenAI."""
    exc = retry_state.outcome.exception()
    if isinstance(exc, RateLimitError):
        try:
            # Honor Retry-After header if present
            retry_after = exc.response.headers.get("Retry-After") if exc.response else None
            if retry_after:
                return float(retry_after)
        except (AttributeError, ValueError, TypeError):
            # Header missing or cast fails, fall back to exponential
            pass
    
    # Fall back to capped exponential backoff (1, 2, 4, 8, 10 seconds)
    return min(2 ** (retry_state.attempt_number - 1), 10)


class EmbeddingGenerator:
    """Generate embeddings via (Azure) OpenAI with batching + retries."""

    # --------------------------------------------------------------------- #
    # Known model families and their default properties. Extend as needed.
    # --------------------------------------------------------------------- #
    _MODEL_REGISTRY: Dict[str, Dict[str, int | bool]] = {
        # Modern models – defaults from the official OpenAI documentation
        #   • text-embedding-3-small  → 1 536 dimensions (optionally 512)
        #   • text-embedding-3-large  → 3 072 dimensions (optionally 1 536)
        #
        # Even though both models support the **dimensions** parameter we store
        # the *server-side default* here.  Callers can still request a
        # smaller size (e.g. 1 536) via the ``dimensions`` constructor
        # argument – *EmbeddingGenerator* will transparently overwrite the
        # *dimension* entry below when an override is supplied.
        "text-embedding-3-small": {
            "dimension": 1536,
            "token_limit": 8000,
            "supports_dimensions_param": True,
        },
        "text-embedding-3-large": {
            "dimension": 3072,
            "token_limit": 8000,
            "supports_dimensions_param": True,
        },
        # Legacy / still-popular model
        "text-embedding-ada-002": {
            "dimension": 1536,
            "token_limit": 8000,
            "supports_dimensions_param": False,
        },
    }

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    def __init__(
        self,
        # Default to *text-embedding-3-small* because its server-side default
        # already matches the 1 536-dimension vector size that both
        # Postgres/pgvector and our default Qdrant collections are created
        # with.  Callers that explicitly need the larger 3 072-dimension
        # variant can still ask for it by passing
        # ``model="text-embedding-3-large", dimensions=3072``.
        model: str = "text-embedding-3-small",
        *,
        dimensions: Optional[int] = 1536,
        encoding_format: Literal["float", "base64"] = "float",
        batch_size: int = 50,
    ):
        """
        Args
        ----
        model
            Either a bare model family (`text-embedding-3-small`) *or*
            an *Azure deployment* in the form ``<deployment>:<model>``.
        dimensions
            Custom output dimensionality (only text-embedding-3 models).
        encoding_format
            `"float"` (default) or `"base64"` – see Azure preview docs.
        batch_size
            OpenAI imposes a hard maximum of 50 inputs per request.
        """
        if ":" in model:
            self.deployment_name, self.model_family = model.split(":", 1)
        else:
            self.deployment_name = self.model_family = model

        self.dimensions = dimensions
        self.encoding_format: Literal["float", "base64"] = encoding_format
        self.batch_size = min(batch_size, 50)

        self._validate_encoding_format()
        self._populate_model_meta()
        self.client: AsyncOpenAI | AsyncAzureOpenAI | None = None
        self._init_client()
        
        # Initialize concurrency limiter
        import asyncio
        self._semaphore = asyncio.Semaphore(settings.embedding_max_concurrency)

    # ------------------------------------------------------------------ #
    # Client initialisation
    # ------------------------------------------------------------------ #
    def _get_current_provider(self) -> str:
        """Get current provider from unified config."""
        try:
            from app.services.unified_config_service import UnifiedConfigService
            from app.database import SessionLocal
            
            with SessionLocal() as db:
                service = UnifiedConfigService(db)
                config = service.get_current_config()
                return config.provider.lower()
        except Exception as e:
            logger.debug(f"Failed to get provider from unified config: {e}")
            return settings.llm_provider.lower()
    def _init_client(self) -> None:
        """Instantiate AsyncOpenAI or AsyncAzureOpenAI client."""
        """Use shared factory helpers to create an SDK client."""

        provider = self._get_current_provider()
        try:
            if provider == "azure":
                from app.llm.client_factory import get_azure_client

                self.client = get_azure_client()
            else:
                from app.llm.client_factory import get_openai_client

                self.client = get_openai_client()
        except Exception as exc:  # pragma: no cover – defensive catch
            logger.error("Embedding client init failed: %s", exc)
            self.client = None

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #
    # Retries only on transient OpenAI errors (rate limit / timeout).
    # Oversized batches are NOT retried as they're deterministic failures.
    @retry(  # noqa: D401 – decorator docs
        stop=stop_after_attempt(settings.embedding_max_retries),
        wait=_adaptive_wait,
        retry=retry_if_exception(_is_retryable_error),
        reraise=True,
    )
    async def generate_embeddings(self, texts: Sequence[str]) -> List[List[float]]:
        """Return embeddings for *texts*, handling retries + validation."""
        if not self.client:
            raise EmbeddingException(
                "Embedding client not initialised", error_code="CLIENT_NOT_INITIALIZED"
            )

        if not texts:
            return []

        # Import batching utilities
        from app.embeddings.batching import iter_token_limited_batches
        from app.monitoring.metrics import record_success

        try:
            all_embeddings: List[List[float]] = []
            start_time = time.time()

            # Use token-aware batching instead of fixed size batching
            token_limit = settings.embedding_model_token_limit
            safety_margin = settings.embedding_safety_margin

            batch_count = 0
            for batch in iter_token_limited_batches(
                list(texts), self.estimate_tokens, token_limit, safety_margin
            ):
                batch_count += 1
                logger.debug(
                    "Processing batch %d with %d texts, estimated %d tokens",
                    batch_count, len(batch),
                    sum(self.estimate_tokens(text) for text in batch)
                )

                # Build kwargs for embedding creation
                kwargs = {
                    "model": self.deployment_name,
                    "input": batch,
                    "encoding_format": self.encoding_format,
                }
                # Only include dimensions if it's specified and supported
                if (self.dimensions is not None and
                        self._model_meta["supports_dimensions_param"]):
                    kwargs["dimensions"] = self.dimensions

                # Use semaphore to limit concurrent requests
                async with self._semaphore:
                    resp = await self.client.embeddings.create(**kwargs)

                for item in resp.data:
                    vector = (
                        self._decode_base64_embedding(item.embedding)
                        if self.encoding_format == "base64"
                        else item.embedding
                    )

                    if not self._validate_dimension(vector):
                        raise VectorDimensionMismatchException(
                            self._model_meta["dimension"], len(vector)
                        )
                    all_embeddings.append(vector)

            # Record success metrics
            duration = time.time() - start_time
            total_tokens = sum(self.estimate_tokens(text) for text in texts)
            record_success(len(all_embeddings), total_tokens, duration)

            logger.info(
                "Generated %d embeddings in %d batches (%s, dim=%d) in %.2fs",
                len(all_embeddings),
                batch_count,
                self.model_family,
                self._model_meta["dimension"],
                duration
            )
            return all_embeddings

        except (AuthenticationError, BadRequestError) as exc:
            logger.error("Embedding generation failed: %s", exc)
            raise EmbeddingException(
                f"Failed to generate embeddings: {exc}", error_code="GENERATION_FAILED"
            ) from exc
        except (RateLimitError, APITimeoutError):
            raise  # handled by tenacity
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Unexpected embedding error", exc_info=True)
            sentry_sdk.capture_exception(exc)
            raise EmbeddingException(
                "Unexpected error during embedding generation",
                error_code="UNKNOWN_ERROR",
            ) from exc

    async def generate_single_embedding(self, text: str) -> List[float]:
        """Convenience wrapper for a single input with caching."""
        # Create cache key from model and text
        cache_key = (self.deployment_name, text)
        
        # Check cache first
        cached_result = await EMBEDDING_CACHE.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for embedding: {len(text)} chars")
            return cached_result
        
        # Generate embedding
        out = await self.generate_embeddings([text])
        result = out[0] if out else []
        
        # Cache the result
        if result:
            await EMBEDDING_CACHE.set(cache_key, result)
            logger.debug(f"Cache miss, stored embedding: {len(text)} chars")
        
        return result

    async def generate_and_store(
        self, chunks: List[CodeEmbedding], db: Session, vector_store=None  # type: ignore [name-defined]
    ) -> None:
        """Create embeddings for *chunks* and persist them in *db* and optionally vector store."""
        if not chunks:
            return

        # Craft high-signal inputs to increase semantic quality
        inputs: List[str] = []
        for c in chunks:
            context = [
                f"Language: {c.document.language}",
                (
                    f"{c.symbol_type} {c.symbol_name}"
                    if c.symbol_type and c.symbol_name
                    else ""
                ),
                f"File: {c.document.file_path}",
                "",
                c.chunk_content,
            ]
            inputs.append("\n".join(filter(None, context)))

        try:
            vectors = await self.generate_embeddings(inputs)

            for chunk, emb in zip(chunks, vectors, strict=True):
                chunk.embedding = emb  # JSON-serialisable
                chunk.embedding_dim = len(emb)

            # Mark related documents as indexed using the already loaded relationship.
            for chunk in chunks:
                if chunk.document and not chunk.document.is_indexed:
                    chunk.document.is_indexed = True

            if isinstance(db, AsyncSession):
                await db.commit()
            else:
                db.commit()

        except (EmbeddingException, VectorDimensionMismatchException):
            if isinstance(db, AsyncSession):
                await db.rollback()
            else:
                db.rollback()
            raise
        except Exception as exc:  # pylint: disable=broad-except
            if isinstance(db, AsyncSession):
                await db.rollback()
            else:
                db.rollback()
            sentry_sdk.capture_exception(exc)
            raise EmbeddingException(
                "Unexpected error during embedding generation and storage",
                error_code="STORE_ERROR",
            ) from exc

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #
    def _populate_model_meta(self) -> None:
        """Set self._model_meta with defaults + custom overrides."""
        meta = self._MODEL_REGISTRY.get(self.model_family)
        if meta is None:
            # Fallback for unknown model families – be permissive
            meta = {
                "dimension": 1536,
                "token_limit": 8000,
                "supports_dimensions_param": False,
            }
        # Apply custom dimension override
        if self.dimensions is not None:
            if not meta["supports_dimensions_param"]:
                raise ValueError(
                    f"Model {self.model_family!r} does not allow "
                    "`dimensions` override"
                )
            meta = {**meta, "dimension": self.dimensions}
        self._model_meta = meta  # e.g. {"dimension": 1024, ...}

    def _validate_encoding_format(self) -> None:
        if self.encoding_format not in ("float", "base64"):
            raise ValueError(
                f"Invalid encoding_format={self.encoding_format!r} "
                "(must be 'float' or 'base64')"
            )

    # Token estimation -------------------------------------------------- #
    def estimate_tokens(self, text: str) -> int:
        """Very rough char→token heuristic (~4 chars per token)."""
        return len(text) // 4

    def _check_token_limits(self, texts: Sequence[str]) -> None:
        """Validate token count (per text & aggregated)."""
        limit = self._model_meta["token_limit"]
        total = 0
        for t in texts:
            n = self.estimate_tokens(t)
            if n > limit:
                raise EmbeddingException(
                    f"Text exceeds token limit: {n} > {limit}",
                    error_code="SINGLE_TEXT_TOO_LARGE",
                )
            total += n
        if total > limit:
            raise EmbeddingException(
                f"Batch too large: {total} tokens > {limit}",
                error_code="INPUT_TOO_LARGE",
            )

    # Dimension helpers ------------------------------------------------- #
    def _validate_dimension(self, emb: Sequence[float]) -> bool:
        return len(emb) == self._model_meta["dimension"]

    # Base64 decoding ---------------------------------------------------- #
    @staticmethod
    def _decode_base64_embedding(b64: str) -> List[float]:
        """Convert base64 string (little-endian float32 array) → list[float]."""
        raw = base64.b64decode(b64)
        dim = len(raw) // 4
        floats = struct.unpack(f"<{dim}f", raw)
        return list(floats)
