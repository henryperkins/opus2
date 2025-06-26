"""
Package initializer for *app.models* (a.k.a. *backend.app.models*).

Exports **all** SQLAlchemy ORM classes so callers can simply:

    >>> from app.models import Project, User, ChatSession, ...

It also resolves the import-path aliasing problem that can cause
SQLAlchemy to see *two* differently-named copies of the same model
class (e.g. ``app.models.Project`` vs ``backend.app.models.Project``).

The trick is to make *both* package names point at the **same**
module object inside ``sys.modules`` and to mirror every already-
imported sub-module from one namespace into the other.

This file must be imported early in application start-up so that **all**
model modules are registered with SQLAlchemy *before* metadata creation.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Public exports – ORM classes                                               #
# --------------------------------------------------------------------------- #

from .base import Base, TimestampMixin
from .user import User
from .session import Session
from .project import Project, ProjectStatus
from .code import CodeDocument, CodeEmbedding
from .embedding import EmbeddingMetadata
from .search_history import SearchHistory
from .import_job import ImportJob, ImportStatus
from .chat import ChatSession, ChatMessage
from .timeline import TimelineEvent
from .config import RuntimeConfig, ConfigHistory
from .prompt import PromptTemplate

__all__ = [
    # infrastructure
    "Base",
    "TimestampMixin",
    # auth / user
    "User",
    "Session",
    # project & code
    "Project",
    "ProjectStatus",
    "CodeDocument",
    "CodeEmbedding",
    # embeddings / search
    "EmbeddingMetadata",
    "SearchHistory",
    "ImportJob",
    "ImportStatus",
    # chat
    "ChatSession",
    "ChatMessage",
    # timeline / config
    "TimelineEvent",
    "RuntimeConfig",
    "ConfigHistory",
    "PromptTemplate",
]

# --------------------------------------------------------------------------- #
# Import-path aliasing                                                       #
# --------------------------------------------------------------------------- #
#
# The test-runner adds the **repository root** to ``sys.path`` which exposes
# *both* the shorthand   ``app.models.*``   **and** the longer
# ``backend.app.models.*`` package hierarchies.  If a given sub-module is
# imported once via each path, Python loads two separate module objects.
#
# SQLAlchemy identifies ORM classes by object identity, so duplicate modules
# create duplicate class objects and trigger:
#
#     sqlalchemy.exc.InvalidRequestError:
#     Multiple classes found for path "Project" in the registry.
#
# To prevent that we (1) register an alias for the package itself and
# (2) mirror every **already-imported** sub-module from one namespace
#     into the other (both directions, just once).
#
# If we ever switch to *lazy* model imports we can re-introduce a meta
# path-finder to keep the two namespaces in sync at import time, but for
# now a one-shot sync during start-up is sufficient.

import sys
from types import ModuleType

# Point *both* package names at the same module object.
sys.modules.setdefault("backend.app.models", sys.modules[__name__])

_PREFIX_APP = "app.models."
_PREFIX_BACKEND = "backend.app.models."


def _alias_submodules(prefix_from: str, prefix_to: str) -> None:
    """Mirror every sub-module under *prefix_from* into *prefix_to*."""
    for name, module in list(sys.modules.items()):
        if not isinstance(module, ModuleType):      # pragma: no cover – defensive
            continue
        if name.startswith(prefix_from):
            suffix = name[len(prefix_from) :]
            target = prefix_to + suffix
            if target not in sys.modules:
                sys.modules[target] = module


# One-time bidirectional sync for everything imported *so far*.
_alias_submodules(_PREFIX_APP, _PREFIX_BACKEND)
_alias_submodules(_PREFIX_BACKEND, _PREFIX_APP)

# --------------------------------------------------------------------------- #
# End of file                                                                 #
# --------------------------------------------------------------------------- #
