"""Minimal stub of *pgvector* and its SQLAlchemy integration for testing.

The real *pgvector* package exposes two main public surfaces that the
code-base touches on import-time:

1. ``pgvector.sqlalchemy.Vector`` – a SQLAlchemy column type.
2. ``pgvector.register_vector`` – helper for psycopg drivers (not
   required in the unit tests).

This stub defines only what is needed to let the repository import all
modules without installing the heavyweight native extension.
"""

from types import ModuleType


class _Vector:  # noqa: D401 – empty placeholder
    def __init__(self, *args, **kwargs):  # noqa: D401 – ignore args
        pass


def register_vector(*_args, **_kwargs):  # noqa: D401 – dummy no-op
    return None


# ---------------------------------------------------------------------------
# sqlalchemy sub-module
# ---------------------------------------------------------------------------


sqlalchemy = ModuleType("pgvector.sqlalchemy")
sqlalchemy.Vector = _Vector


# Make ``import pgvector.sqlalchemy`` work

import sys as _sys


_sys.modules[sqlalchemy.__name__] = sqlalchemy

__all__ = ["register_vector", "sqlalchemy"]
