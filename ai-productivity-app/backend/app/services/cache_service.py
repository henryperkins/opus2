"""Advanced caching and performance optimization service."""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from functools import wraps
import hashlib
import pickle
from dataclasses import dataclass
from collections import defaultdict, OrderedDict

import redis
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    timestamp: float
    ttl: Optional[float] = None
    access_count: int = 0
    last_accessed: float = 0
    size_bytes: int = 0
    tags: List[str] = None

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def is_stale(self, stale_threshold: float = 300) -> bool:
        """Check if cache entry is stale (old but not expired)."""
        return time.time() - self.timestamp > stale_threshold


class CacheMetrics:
    """Cache performance metrics."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expired_items = 0
        self.total_size = 0
        self.start_time = time.time()
        self.operation_times = defaultdict(list)

    def record_hit(self, operation_time: float = 0):
        """Record cache hit."""
        self.hits += 1
        if operation_time > 0:
            self.operation_times["hit"].append(operation_time)

    def record_miss(self, operation_time: float = 0):
        """Record cache miss."""
        self.misses += 1
        if operation_time > 0:
            self.operation_times["miss"].append(operation_time)

    def record_eviction(self):
        """Record cache eviction."""
        self.evictions += 1

    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.get_hit_rate(),
            "evictions": self.evictions,
            "expired_items": self.expired_items,
            "total_size": self.total_size,
            "uptime": time.time() - self.start_time,
            "avg_hit_time": (
                sum(self.operation_times["hit"]) / len(self.operation_times["hit"])
                if self.operation_times["hit"]
                else 0
            ),
            "avg_miss_time": (
                sum(self.operation_times["miss"]) / len(self.operation_times["miss"])
                if self.operation_times["miss"]
                else 0
            ),
        }


class MultiLevelCache:
    """Multi-level cache with L1 (memory) and L2 (Redis) tiers."""

    def __init__(
        self,
        l1_max_size: int = 1000,
        l1_ttl: float = 300,  # 5 minutes
        l2_ttl: float = 3600,  # 1 hour
        redis_client: Optional[redis.Redis] = None,
    ):
        self.l1_cache = OrderedDict()  # LRU cache
        self.l1_max_size = l1_max_size
        self.l1_ttl = l1_ttl
        self.l2_ttl = l2_ttl
        self.metrics = CacheMetrics()

        # Redis client for L2 cache
        self.redis_client = redis_client or self._create_redis_client()
        self.redis_available = self._test_redis_connection()

        # Cache warming and cleanup
        self._last_cleanup = time.time()
        self._cleanup_interval = 60  # Clean every minute

    def _create_redis_client(self) -> Optional[redis.Redis]:
        """Create Redis client if available."""
        try:
            if hasattr(settings, "REDIS_URL") and settings.REDIS_URL:
                return redis.from_url(settings.REDIS_URL, decode_responses=False)
            return None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            return None

    def _test_redis_connection(self) -> bool:
        """Test Redis connection."""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False

    def _generate_key(self, key: str, prefix: str = "cache") -> str:
        """Generate cache key with prefix."""
        return f"{prefix}:{key}"

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        return pickle.dumps(value)

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        return pickle.loads(data)

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes."""
        try:
            return len(pickle.dumps(value))
        except Exception:
            return len(str(value).encode())

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with L1 -> L2 fallback."""
        start_time = time.time()

        # Check L1 cache first
        if key in self.l1_cache:
            entry = self.l1_cache[key]
            if not entry.is_expired():
                # Move to end (LRU)
                self.l1_cache.move_to_end(key)
                entry.access_count += 1
                entry.last_accessed = time.time()

                self.metrics.record_hit(time.time() - start_time)
                return entry.value
            else:
                # Remove expired entry
                del self.l1_cache[key]
                self.metrics.expired_items += 1

        # Check L2 cache (Redis)
        if self.redis_available:
            try:
                redis_key = self._generate_key(key)
                data = self.redis_client.get(redis_key)
                if data:
                    value = self._deserialize_value(data)

                    # Promote to L1 cache
                    await self._set_l1(key, value, self.l1_ttl)

                    self.metrics.record_hit(time.time() - start_time)
                    return value
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # Cache miss
        self.metrics.record_miss(time.time() - start_time)
        return default

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set value in both L1 and L2 caches."""
        try:
            # Set in L1 cache
            await self._set_l1(key, value, ttl or self.l1_ttl)

            # Set in L2 cache (Redis)
            if self.redis_available:
                try:
                    redis_key = self._generate_key(key)
                    data = self._serialize_value(value)
                    redis_ttl = int(ttl or self.l2_ttl)
                    self.redis_client.setex(redis_key, redis_ttl, data)
                except Exception as e:
                    logger.warning(f"Redis set failed: {e}")

            return True
        except Exception as e:
            logger.error(f"Cache set failed: {e}")
            return False

    async def _set_l1(self, key: str, value: Any, ttl: float):
        """Set value in L1 cache."""
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl,
            size_bytes=self._calculate_size(value),
        )

        # Add to cache
        self.l1_cache[key] = entry
        self.l1_cache.move_to_end(key)

        # Evict if necessary
        while len(self.l1_cache) > self.l1_max_size:
            oldest_key = next(iter(self.l1_cache))
            del self.l1_cache[oldest_key]
            self.metrics.record_eviction()

        # Update metrics
        self.metrics.total_size += entry.size_bytes

    async def delete(self, key: str) -> bool:
        """Delete from both caches."""
        deleted = False

        # Delete from L1
        if key in self.l1_cache:
            del self.l1_cache[key]
            deleted = True

        # Delete from L2 (Redis)
        if self.redis_available:
            try:
                redis_key = self._generate_key(key)
                self.redis_client.delete(redis_key)
                deleted = True
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

        return deleted

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching pattern."""
        cleared = 0

        # Clear L1 cache
        if pattern:
            keys_to_remove = [k for k in self.l1_cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.l1_cache[key]
                cleared += 1
        else:
            cleared += len(self.l1_cache)
            self.l1_cache.clear()

        # Clear L2 cache (Redis)
        if self.redis_available:
            try:
                if pattern:
                    redis_pattern = self._generate_key(f"*{pattern}*")
                    keys = self.redis_client.keys(redis_pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                        cleared += len(keys)
                else:
                    # Clear all cache keys
                    keys = self.redis_client.keys(self._generate_key("*"))
                    if keys:
                        self.redis_client.delete(*keys)
                        cleared += len(keys)
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")

        return cleared

    async def cleanup(self):
        """Clean up expired entries."""
        current_time = time.time()

        # Skip if cleanup was recent
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        # Clean L1 cache
        expired_keys = [
            key for key, entry in self.l1_cache.items() if entry.is_expired()
        ]

        for key in expired_keys:
            del self.l1_cache[key]
            self.metrics.expired_items += 1

        self._last_cleanup = current_time

        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = self.metrics.get_stats()
        stats.update(
            {
                "l1_entries": len(self.l1_cache),
                "l1_max_size": self.l1_max_size,
                "l2_available": self.redis_available,
                "memory_usage": sum(
                    entry.size_bytes for entry in self.l1_cache.values()
                ),
            }
        )
        return stats


class CacheService:
    """High-level cache service with specialized caching strategies."""

    def __init__(self):
        self.cache = MultiLevelCache()

        # Specialized caches
        self.embedding_cache = MultiLevelCache(l1_max_size=500, l1_ttl=1800)  # 30 min
        self.query_cache = MultiLevelCache(l1_max_size=200, l1_ttl=600)  # 10 min
        self.search_cache = MultiLevelCache(l1_max_size=300, l1_ttl=900)  # 15 min

    def _hash_key(self, key: str) -> str:
        """Create hash-based cache key."""
        return hashlib.md5(key.encode()).hexdigest()

    async def cache_embedding(
        self, text: str, embedding: List[float], ttl: float = 3600
    ):
        """Cache text embedding."""
        key = f"embedding:{self._hash_key(text)}"
        await self.embedding_cache.set(key, embedding, ttl)

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding."""
        key = f"embedding:{self._hash_key(text)}"
        return await self.embedding_cache.get(key)

    async def cache_query_result(self, query: str, result: Any, ttl: float = 600):
        """Cache query result."""
        key = f"query:{self._hash_key(query)}"
        await self.query_cache.set(key, result, ttl)

    async def get_query_result(self, query: str) -> Any:
        """Get cached query result."""
        key = f"query:{self._hash_key(query)}"
        return await self.query_cache.get(key)

    async def cache_search_result(
        self, query: str, filters: Dict[str, Any], result: Any, ttl: float = 900
    ):
        """Cache search result with filters."""
        filter_key = json.dumps(filters, sort_keys=True)
        key = f"search:{self._hash_key(query + filter_key)}"
        await self.search_cache.set(key, result, ttl)

    async def get_search_result(self, query: str, filters: Dict[str, Any]) -> Any:
        """Get cached search result."""
        filter_key = json.dumps(filters, sort_keys=True)
        key = f"search:{self._hash_key(query + filter_key)}"
        return await self.search_cache.get(key)

    async def invalidate_document_cache(self, document_id: int):
        """Invalidate all cache entries related to a document."""
        await self.cache.clear(f"doc:{document_id}")
        await self.search_cache.clear("")  # Clear all search results
        await self.query_cache.clear("")  # Clear all query results

    async def warm_cache(self, popular_queries: List[str]):
        """Warm cache with popular queries."""
        # This would be implemented with actual query execution
        logger.info(f"Cache warming initiated for {len(popular_queries)} queries")

    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get stats from all cache instances."""
        return {
            "general": self.cache.get_stats(),
            "embeddings": self.embedding_cache.get_stats(),
            "queries": self.query_cache.get_stats(),
            "search": self.search_cache.get_stats(),
        }


def cache_result(cache_key_func=None, ttl: float = 600):
    """Decorator for caching function results."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Try to get from cache
            cached_result = await cache_service.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


# Global cache service instance
cache_service = CacheService()
