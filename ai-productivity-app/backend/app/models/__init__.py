# Model package exports
from .base import Base, TimestampMixin
from .user import User
from .session import Session
# Import Phase-4 models so they are registered with SQLAlchemy before metadata
# creation.  These imports must remain *after* Base to avoid circular deps.
from .project import Project, ProjectStatus
from .code import CodeDocument, CodeEmbedding
from .search_history import SearchHistory
from .import_job import ImportJob, ImportStatus
from .chat import ChatSession, ChatMessage
from .timeline import TimelineEvent
from .config import RuntimeConfig, ConfigHistory

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Session",
    "Project",
    "ProjectStatus",
    "CodeDocument",
    "CodeEmbedding",
    "SearchHistory",
    "ImportJob",
    "ImportStatus",
    "ChatSession",
    "ChatMessage",
    "TimelineEvent",
    "RuntimeConfig",
    "ConfigHistory",
]

# ---------------------------------------------------------------------------
# Import-path *aliasing* ------------------------------------------------------
# ---------------------------------------------------------------------------
#
# The test-runner collects the repository from its **root** directory which
# places both the top-level *backend/* package *and* its child package
# hierarchy on ``sys.path``.  Depending on the exact import order this can
# lead to the **same** module being loaded twice – once via the canonical short
# path (``app.models.<sub>``) and a second time via the longer
# ``backend.app.models.<sub>`` path.  SQLAlchemy identifies ORM classes by
# **object identity**, therefore two different *module* objects that both
# define a ``Project`` class are interpreted as two *independent* model
# classes.  Relationship strings such as ``relationship("Project")`` become
# ambiguous and SQLAlchemy aborts the Mapper configuration with the infamous
# *Multiple classes found for path "Project"* error.
#
# To guarantee that *all* import paths return the *same* module object we
# publish aliases in ``sys.modules`` for both directions:  if a sub-module is
# imported under ``app.models.<sub>`` we expose it under the corresponding
# ``backend.app.models.<sub>`` name – and vice-versa.  This single, central
# shim covers *every* model file without having to repeat the aliasing snippet
# in every module.
# ---------------------------------------------------------------------------

from types import ModuleType as _ModuleType
import sys as _sys

# Map *this* package itself first so that both base package names resolve to
# the identical module object.
_sys.modules.setdefault("backend.app.models", _sys.modules[__name__])

# Mirror already-imported sub-modules of *either* path onto the counterpart.
_PREFIX_APP = "app.models."
_PREFIX_BACKEND = "backend.app.models."


def _alias_submodules(prefix_from: str, prefix_to: str) -> None:  # noqa: D401
    """Expose every module under *prefix_from* also under *prefix_to*."""

    for _name, _module in list(_sys.modules.items()):
        if not isinstance(_module, _ModuleType):  # pragma: no cover – defensive
            continue
        if _name.startswith(prefix_from):
            _sub = _name[len(prefix_from) :]
            _target = prefix_to + _sub
            if _target not in _sys.modules:
                _sys.modules[_target] = _module

# Perform a one-time synchronisation for modules that have been imported up to
# this point.
_alias_submodules(_PREFIX_APP, _PREFIX_BACKEND)
_alias_submodules(_PREFIX_BACKEND, _PREFIX_APP)

# ---------------------------------------------------------------------------
# For now the *static* one-time synchronisation above is sufficient because all
# model sub-modules are imported eagerly at application start-up.  Should we
# ever migrate to *lazy* model loading we can revisit this and install a small
# import hook to mirror future imports as well (see git history for a possible
# implementation).  Removing the hook avoids the risk of subtle recursion
# issues inside Python's import machinery.
# ---------------------------------------------------------------------------

