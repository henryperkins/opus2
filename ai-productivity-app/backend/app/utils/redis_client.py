"""
redis_rate_limiter.py – Distributed rate limiter backed by Redis/Lua.

Public API:
    * get_redis()                     – connection factory (async)
    * close_redis()                   – shutdown hook
    * rate_limit(...) -> headers dict – raises HTTP 429 on excess
"""

from __future__ import annotations

# stdlib
import asyncio
import logging
import os
import time
from functools import lru_cache
from typing import Dict, Final, Optional, Tuple

# --------------------------------------------------------------------------- #
# Optional dependency: redis-py (asyncio variant)
# --------------------------------------------------------------------------- #
# The test environment inside the Codex sandbox may not have the *redis* wheel
# installed and outbound network access is disabled so we cannot `pip install`
# it on-the-fly.  To keep the application importable – and to allow unit tests
# that exercise the *rate_limit* helper – we fall back to an **in-memory**
# stub that fulfils the tiny subset of the redis-py API required by this
# module.
#
# When the real library **is** available the stub remains unused and the full
# Redis functionality (including Lua scripting and atomic counters) is
# leveraged.
# --------------------------------------------------------------------------- #

try:
    import redis.asyncio as redis  # type: ignore

    _HAS_REDIS: Final[bool] = True
except ModuleNotFoundError:  # pragma: no cover – fallback for CI without redis
    _HAS_REDIS = False  # type: ignore

    logger_stub = logging.getLogger(__name__)

    class _MemoryRedis:  # pylint: disable=too-few-public-methods
        """Extremely small in-memory subset of redis.asyncio.Redis."""

        # Internal storage – key -> [hits, first_timestamp]
        _counter: Dict[str, Tuple[int, float]] = {}

        # Public API -----------------------------------------------------------------
        async def ping(self) -> bool:  # noqa: D401
            return True

        # Lua *eval* call – we only ever call it with the *sliding window* script
        # in :pyfunc:`rate_limit`.  Therefore we replicate the logic directly.
        async def eval(  # noqa: D401
            self,
            _script: str,
            *,
            numkeys: int,  # noqa: D401 – kept for signature parity
            keys: list[str],
            args: list[int | str],
        ) -> int:
            if numkeys != 1:
                raise ValueError("In-memory stub only supports 1 key")

            key = keys[0]
            if len(args) != 2:
                raise ValueError("Stub expects limit and window args")

            limit, window = int(args[0]), int(args[1])
            now = time.time()

            hits, first_ts = self._counter.get(key, (0, now))

            # Reset bucket when window elapsed
            if now - first_ts >= window:
                hits, first_ts = 0, now

            hits += 1
            self._counter[key] = (hits, first_ts)
            return hits

        async def ttl(self, key: str) -> int:  # noqa: D401
            if key not in self._counter:
                return -2  # key does not exist

            _hits, first_ts = self._counter[key]
            now = time.time()
            # We do not store *window* per key; for TTL we approximate by
            # returning remaining time until *rate_limit* window (60s default)
            window = 60
            remaining = int(max(0, window - (now - first_ts)))
            return remaining if remaining > 0 else -2

        # Keys / set / get are used by health-check heartbeat only.  Provide
        # minimal, non-persistent implementations so the endpoints work.
        _kv: Dict[str, str] = {}

        async def set(self, key: str, value: str, *, ex: int | None = None):  # noqa: D401
            self._kv[key] = value  # TTL ignored in stub

        async def get(self, key: str) -> Optional[str]:  # noqa: D401
            return self._kv.get(key)

        async def keys(self, pattern: str):  # noqa: D401
            from fnmatch import fnmatch
            return [k for k in self._kv if fnmatch(k, pattern)]

        # Additional helper used by health-check ---------------------------------

        async def info(self, section: str | None = None):  # noqa: D401  – signature parity
            """Return fake memory info required by readiness probe."""

            # Provide only the *used_memory* field – enough for monitoring
            if section in (None, "memory"):
                return {"used_memory": 0}
            return {}

        async def close(self):  # noqa: D401
            return

    # Expose stub under the same name as the real package so the rest of the
    # module remains unchanged.
    import types  # noqa: E402  – after stub class creation

    redis = types.ModuleType("redis.asyncio")  # type: ignore
    # Expose the minimal API surface used by the production code so that
    # import-sites do not fail when the real *redis* package is unavailable.
    redis.Redis = _MemoryRedis  # type: ignore

    def _from_url(*_args, **_kwargs):  # noqa: D401  – signature compatibility
        """Return an in-memory Redis replacement (stub helper)."""

        return _MemoryRedis()

    redis.from_url = _from_url  # type: ignore[attr-defined]

    logger_stub.warning(
        "redis-py is not installed; falling back to in-memory stub. "
        "Rate-limiting will not be shared across processes."
    )

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
            1,  # numkeys
            key,  # keys
            limit, window,  # args
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
