"""
redis_rate_limiter.py – Distributed rate limiter backed by Redis/Lua.

Public API:
    * get_redis()                     – connection factory (async)
    * close_redis()                   – shutdown hook
    * rate_limit(...) -> headers dict – raises HTTP 429 on excess
"""

from __future__ import annotations

import os
import logging
from functools import lru_cache
from typing import Final, Dict

import redis.asyncio as redis
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Redis connection helpers
# --------------------------------------------------------------------------- #


def _redis_url() -> str:
    """Return Redis connection URL from env or default."""
    return (
        os.getenv("REDIS_URL")
        or os.getenv("REDIS_SENTINEL_URL")         # compat
        or "redis://localhost:6379/0"
    )


@lru_cache(maxsize=1)  # one pool per process
def _create_pool() -> redis.Redis:
    pool = redis.from_url(
        _redis_url(),
        encoding="utf-8",
        decode_responses=True,
        max_connections=100,
    )
    return pool


async def get_redis() -> redis.Redis:
    """Return a connected Redis client (lazy-initialised)."""
    client = _create_pool()
    try:
        # cheap NOOP if pool already warm
        await client.ping()
    except Exception as exc:  # pragma: no cover
        logger.error("Redis ping failed: %s", exc)
        raise
    return client


async def close_redis() -> None:
    """Close the process-local Redis pool (to be called in shutdown event)."""
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
    Enforce <limit> requests per <window> seconds for the given key.

    Returns headers to be merged into the FastAPI Response on success.
    Raises HTTPException 429 on violation.

    Set fail_open=False to block requests if Redis is unavailable.
    """
    # Fast bypass toggle for unit-tests
    if os.getenv("DISABLE_RATE_LIMITER", "false").lower() == "true":
        return {}

    try:
        redis_client = await get_redis()

        count: int = await redis_client.eval(
            _LUA_SLIDING_WINDOW,
            numkeys=1,
            keys=[key],
            args=[limit, window],
        )

        if count > limit:
            ttl = await redis_client.ttl(key)
            # ttl can be -1 (no expiry) or -2 (key lost); normalise
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
            # RFC: send reset to help clients schedule retries
            "X-RateLimit-Reset": str(await redis_client.ttl(key)),
        }

    except redis.RedisError as exc:  # pragma: no cover
        logger.error("Redis rate-limit error (%s). fail_open=%s", exc,
                     fail_open)
        if not fail_open:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate-limiting service temporarily unavailable.",
            ) from exc
        return {}  # allow request


# --------------------------------------------------------------------------- #
# Deprecated alias
# --------------------------------------------------------------------------- #

async def enforce_redis_rate_limit(
    key: str,
    limit: int,
    window: int,
    error_detail: str = "Rate limit exceeded. Please try again later.",
) -> Dict[str, str]:
    """Backward-compat shim."""
    logger.warning("Deprecated: use rate_limit() instead.")
    return await rate_limit(key, limit, window, error_detail=error_detail)
