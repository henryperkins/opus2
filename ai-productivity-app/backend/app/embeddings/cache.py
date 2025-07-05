"""Simple in-process LRU cache for generated embeddings.

This lightweight cache avoids round-trips to the OpenAI / Azure OpenAI
embedding endpoint when the *same* text is embedded repeatedly (for instance
every time a user submits an identical search query).  The cache lives in the
Python process and therefore has the same lifecycle as the FastAPI
application – it is automatically cleared on restart or redeploy which keeps
the implementation simple and free of external dependencies like Redis.

Key design goals
----------------
1. **Tiny footprint** – store only the raw embedding list returned by the
   SDK.  We cap the size to a few thousand entries which translates to a
   handful of MiB at most (e.g. 1 000 × 1 536 × 4 bytes ≈ 6 MiB).
2. **Concurrency-safe** – although `asyncio` runs single-threaded we still
   protect the critical sections with a *non-blocking* lock so that multiple
   overlapping requests do not attempt to insert the same key at the same
   time.
3. **Zero external deps** – implemented with `collections.OrderedDict`.

If a future version needs to share the cache across *multiple* replica the
module can be swapped for a small Redis wrapper without touching the
down-stream usage in `EmbeddingGenerator`.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# A modest default that covers typical autocomplete use-cases while keeping
# memory usage bounded.  The constant may be tuned via the environment
# variable *EMBEDDING_CACHE_SIZE* without requiring code changes.

import os


DEFAULT_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "1024"))


class _LRUCache:
    """Tiny *Least-Recently-Used* cache with a fixed maximum size."""

    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE):
        self.max_size = max_size
        self._data: "OrderedDict[Tuple[str, str], List[float]]" = OrderedDict()
        # `asyncio.Lock` so that *await* works smoothly in async contexts
        self._lock = asyncio.Lock()

    async def get(self, key: Tuple[str, str]) -> Optional[List[float]]:
        """Return the cached value or ``None`` when the key is missing."""
        # We acquire the lock in *shared* mode because `.pop` + re-insert is a
        # mutation that has to stay atomic.
        async with self._lock:
            try:
                value = self._data.pop(key)
            except KeyError:
                return None
            # Re-insert to mark as *most recently used*
            self._data[key] = value
            return value

    async def set(self, key: Tuple[str, str], value: List[float]) -> None:
        """Insert *value* under *key* and evict oldest entries if necessary."""
        async with self._lock:
            if key in self._data:
                # Refresh position – simpler than testing separately
                self._data.pop(key, None)
            self._data[key] = value

            # Evict in insertion order until size under limit
            while len(self._data) > self.max_size:
                self._data.popitem(last=False)


# Singleton instance that can be imported from anywhere in the backend.
EMBEDDING_CACHE: _LRUCache = _LRUCache()
