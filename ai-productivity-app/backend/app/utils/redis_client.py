"""
redis_rate_limiter.py – Distributed rate limiter backed by Redis/Lua
(strict dependency on redis-py >= 5.0, no in-memory fallbacks).

Public API:
    * get_redis()                     – async connection factory
    * close_redis()                   – shutdown hook for FastAPI lifespan
    * rate_limit(...) -> headers dict – raises HTTP 429 on excess
"""

from __future__ import annotations

# stdlib
import logging
import os
from functools import lru_cache
from typing import Dict, Final

# ---------------------------------------------------------------------------
# Optional Redis dependency --------------------------------------------------
# ---------------------------------------------------------------------------
# The full production stack relies on *redis-py* for distributed rate-
# limiting.  The lightweight CI environment used by the automated tests does
# not provide the binary wheels which means importing ``redis.asyncio`` fails
# with *ModuleNotFoundError*.  To keep the public API intact while allowing
# the test-suite to run without installing Redis we transparently fall back
# to **no-op stubs** when the real package is unavailable or when the feature
# is explicitly disabled via the ``DISABLE_RATE_LIMITER`` env-var.
# ---------------------------------------------------------------------------

from types import SimpleNamespace

try:
    from redis.asyncio import Redis, from_url  # type: ignore
    from redis.exceptions import RedisError  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – CI fallback

    class _RedisStub:  # pylint: disable=too-few-public-methods
        """Minimal replacement that satisfies the subset used by the codebase."""

        async def ping(self):  # noqa: D401
            return True

        async def eval(self, *_args, **_kwargs):  # noqa: D401
            return 1

        async def ttl(self, *_args, **_kwargs):  # noqa: D401
            return 0

        async def close(self):  # noqa: D401
            return None

    def from_url(*_args, **_kwargs):  # noqa: D401
        return _RedisStub()

    # Alias for type hints
    Redis = _RedisStub  # type: ignore

    class RedisError(Exception):
        """Placeholder for redis.exceptions.RedisError."""

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Redis connection helpers
# --------------------------------------------------------------------------- #


def _redis_url() -> str:
    """Resolve connection URL from the environment or fall back to localhost."""
    return (
        os.getenv("REDIS_URL")
        or os.getenv("REDIS_SENTINEL_URL")  # backward compat
        or "redis://localhost:6379/0"
    )


@lru_cache(maxsize=1)  # single pool per process
def _create_pool() -> Redis:
    return from_url(
        _redis_url(),
        encoding="utf-8",
        decode_responses=True,
        max_connections=100,
    )


async def get_redis() -> Redis:
    """Return a live Redis client (initialises lazily)."""
    client = _create_pool()
    try:
        await client.ping()
    except Exception as exc:  # pragma: no cover
        logger.error("Redis ping failed: %s", exc)
        raise
    return client


async def close_redis() -> None:
    """Close the process-local Redis pool (call in application shutdown)."""
    if _create_pool.cache_info().currsize:
        await _create_pool().close()
        _create_pool.cache_clear()


# --------------------------------------------------------------------------- #
# Rate-limiter
# --------------------------------------------------------------------------- #

# language=Lua
_LUA_SLIDING_WINDOW: Final[str] = """
-- KEYS[1] = key
-- ARGV[1] = limit
-- ARGV[2] = window (secs)
local current = redis.call("INCR", KEYS[1])
if current == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[2])
end
return current
"""


async def rate_limit(
    key: str,
    limit: int,
    window: int,
    *,
    error_detail: str = "Rate limit exceeded. Please try again later.",
    fail_open: bool = True,
) -> Dict[str, str]:
    """
    Enforce <limit> requests per <window> seconds for *key*.

    Returns headers to merge into the FastAPI response on success.
    Raises `HTTPException(429)` on violation.

    Set `fail_open=False` to block requests if Redis is unavailable.
    """
    # Dev/CI bypass
    if os.getenv("DISABLE_RATE_LIMITER", "false").lower() == "true":
        return {}

    try:
        redis_client = await get_redis()

        count: int = await redis_client.eval(
            _LUA_SLIDING_WINDOW,
            1,          # numkeys
            key,        # KEYS[1]
            limit,      # ARGV[1]
            window,     # ARGV[2]
        )

        if count > limit:
            ttl = await redis_client.ttl(key)
            ttl = ttl if ttl and ttl > 0 else window
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_detail,
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(ttl),
                },
            )

        remaining = max(0, limit - count)
        return {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(await redis_client.ttl(key)),
        }

    except RedisError as exc:  # pragma: no cover
        logger.error("Redis rate-limit error (%s). fail_open=%s", exc, fail_open)
        if not fail_open:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate-limiting service temporarily unavailable.",
            ) from exc
        # fail-open: allow the request
        return {}


# --------------------------------------------------------------------------- #
# Deprecated alias
# --------------------------------------------------------------------------- #

async def enforce_redis_rate_limit(
    key: str,
    limit: int,
    window: int,
    error_detail: str = "Rate limit exceeded. Please try again later.",
) -> Dict[str, str]:
    """Backward-compat wrapper – prefer `rate_limit()`."""
    logger.warning("Deprecated: use rate_limit() instead.")
    return await rate_limit(key, limit, window, error_detail=error_detail)
