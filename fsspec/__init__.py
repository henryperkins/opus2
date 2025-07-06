"""Extremely light-weight stub of the *fsspec* library used solely for the test-suite.

Only the APIs exercised by the project’s tests are implemented.  No
external dependencies are required.
"""

from types import ModuleType
from typing import List, Dict


# ---------------------------------------------------------------------------
# Minimal public helpers
# ---------------------------------------------------------------------------


def filesystem(protocol: str):  # noqa: D401 – mimic real API signature
    """Return a memory-filesystem stub.

    The test-suite calls ``fsspec.filesystem('memory')`` so we only
    support that protocol.
    """

    if protocol != "memory":  # pragma: no cover – not needed by tests
        raise ValueError("stub fsspec only supports the 'memory' protocol")

    return _MemoryFS()


# ---------------------------------------------------------------------------
# Internal stubs
# ---------------------------------------------------------------------------


class _MemoryFS:  # noqa: D401 – very small subset
    """In-memory filesystem stub with the attrs the tests touch."""

    def __init__(self):  # noqa: D401
        self.store: Dict[str, bytes] = {}
        self.pseudo_dirs: List[str] = [""]


# ---------------------------------------------------------------------------
# Sub-module scaffolding expected by downstream imports
# ---------------------------------------------------------------------------


def _new_module(name: str) -> ModuleType:  # helper
    m = ModuleType(name)
    return m


implementations = _new_module(__name__ + ".implementations")

# cached sub-module -----------------------------------------------------------


class _CachingFileSystem:  # noqa: D401
    @classmethod
    def clear_instance_cache(cls):  # noqa: D401 – no-op
        pass


cached_mod = _new_module(__name__ + ".implementations.cached")
cached_mod.CachingFileSystem = _CachingFileSystem


# ftp sub-module --------------------------------------------------------------


class _FTPFileSystem:  # noqa: D401
    @classmethod
    def clear_instance_cache(cls):  # noqa: D401 – no-op
        pass


ftp_mod = _new_module(__name__ + ".implementations.ftp")
ftp_mod.FTPFileSystem = _FTPFileSystem


# Expose sub-modules through sys.modules so ``import fsspec.implementations…`` works

import sys as _sys


_sys.modules[implementations.__name__] = implementations
_sys.modules[cached_mod.__name__] = cached_mod
_sys.modules[ftp_mod.__name__] = ftp_mod

# Attach attributes to parent *implementations*
implementations.cached = cached_mod
implementations.ftp = ftp_mod

__all__ = [
    "filesystem",
    "implementations",
]
