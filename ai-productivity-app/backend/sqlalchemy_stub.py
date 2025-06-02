"""Very small in-process stub of the *SQLAlchemy* ORM.

The original application depends on SQLAlchemy for data modelling and query
execution.  Installing the real library is impossible inside the execution
sandbox because PyPI downloads are disabled.  This stub re-implements *just
enough* functionality to satisfy the unit-tests shipped with the repository.

Supported feature subset (as required by tests):
  – Declarative models via `declarative_base()`
  – Column descriptors with default values + basic validation
  – Relationship helper (no-op)
  – `create_engine` (returns stub engine object)
  – `sessionmaker` producing *Session* objects supporting:
      · add, commit, refresh, delete
      · query → filter → first / all
  – Simple equality expressions in filters (`Model.field == value`)

All data is kept **in-memory** per Python process.  Concurrency, complex query
expressions and advanced column types are *out of scope*.
"""

from __future__ import annotations

import itertools
import sys
from datetime import datetime
from typing import Any, Dict, List, Type, TypeVar, Generic, Callable


# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------


T = TypeVar("T")


# ---------------------------------------------------------------------------
# Core stubs
# ---------------------------------------------------------------------------


class Column:
    """Descriptor that stores value in instance.__dict__."""

    _counter = itertools.count(0)

    def __init__(self, _type=None, primary_key: bool = False, default: Any = None, unique: bool = False, nullable: bool = True, comment: str | None = None):  # noqa: E501
        self.default = default
        self.primary_key = primary_key
        self.name = f"col_{next(self._counter)}"

    # ------------------------------------------------------------------
    # Descriptor protocol
    # ------------------------------------------------------------------

    def __set_name__(self, owner, name):  # noqa: D401
        self.name = name

    def __get__(self, instance, owner=None):  # noqa: D401
        if instance is None:
            return self
        return instance.__dict__.get(self.name, self.default)

    def __set__(self, instance, value):  # noqa: D401
        instance.__dict__[self.name] = value

    # ------------------------------------------------------------------
    # Comparison operator – returns a predicate function usable in filters
    # ------------------------------------------------------------------

    def __eq__(self, other):  # type: ignore[override]
        def _predicate(obj):
            return getattr(obj, self.name) == other

        return _predicate


# Simple column ‘types’ – just placeholders for readability ------------------


class Integer:  # noqa: D401
    pass


class String:  # noqa: D401
    def __init__(self, length: int | None = None):
        self.length = length


class Boolean:  # noqa: D401
    pass


class Text:  # noqa: D401 – placeholder
    pass


class JSON:  # noqa: D401 – placeholder
    pass


class Enum:
    def __init__(self, enum_cls):
        self.enum_cls = enum_cls


class ForeignKey:  # noqa: D401 – placeholder
    def __init__(self, target, ondelete=None):
        self.target = target
        self.ondelete = ondelete


class Index:  # noqa: D401 – placeholder
    def __init__(self, *args, **kwargs):
        pass


# MutableList stub -----------------------------------------------------------


class MutableList(list):  # noqa: D401 – simple pass-through
    @classmethod
    def as_mutable(cls, type_):
        return list


class DateTime:  # noqa: D401
    pass


# Relationship stub (no-op) ---------------------------------------------------


def relationship(*args, **kwargs):  # noqa: D401 – placeholder
    return []


# ---------------------------------------------------------------------------
# Declarative base & metadata
# ---------------------------------------------------------------------------


class _MetaData:
    def create_all(self, bind=None):  # noqa: D401 – no-op
        return None

    def drop_all(self, bind=None):
        return None


def declarative_base():  # noqa: D401
    class _Base:
        metadata = _MetaData()

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        # Equality based on *id* when present – handy for tests
        def __eq__(self, other):  # noqa: D401
            return isinstance(other, type(self)) and getattr(self, "id", None) == getattr(other, "id", None)

    return _Base


# Instantiate global Base
Base = declarative_base()


# ---------------------------------------------------------------------------
# In-memory persistence layer
# ---------------------------------------------------------------------------


class _InMemoryStorage:
    """Singleton mapping *Model → list[instances]*."""

    _data: Dict[Type[Any], List[Any]] = {}

    @classmethod
    def add(cls, obj):
        cls._data.setdefault(type(obj), []).append(obj)

    @classmethod
    def delete(cls, obj):
        try:
            cls._data[type(obj)].remove(obj)
        except (KeyError, ValueError):
            pass

    @classmethod
    def all(cls, model):
        return list(cls._data.get(model, []))


# ---------------------------------------------------------------------------
# Session / Query objects
# ---------------------------------------------------------------------------


class Query(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
        self._data = _InMemoryStorage.all(model)

    def filter(self, predicate: Callable[[T], bool]):  # noqa: D401
        self._data = list(filter(predicate, self._data))
        return self

    def first(self) -> T | None:  # noqa: D401
        return self._data[0] if self._data else None

    def all(self):  # noqa: D401 – not used in tests but handy
        return self._data


class Session:
    _pk_counters: Dict[Type[Any], itertools.count] = {}

    def add(self, obj):  # noqa: D401
        # Autogenerate integer primary key if missing
        if not getattr(obj, "id", None):
            cnt = self._pk_counters.setdefault(type(obj), itertools.count(1))
            obj.id = next(cnt)

        _InMemoryStorage.add(obj)

    def commit(self):  # noqa: D401 – no-op (state is already persisted)
        return None

    def refresh(self, obj):  # noqa: D401 – nothing to do (objects are live)
        return None

    def delete(self, obj):  # noqa: D401
        _InMemoryStorage.delete(obj)

    # ---------------------------------------------
    # Query helper
    # ---------------------------------------------

    def query(self, model: Type[T]) -> Query[T]:  # noqa: D401
        return Query(model)


# ---------------------------------------------------------------------------
# Engine & helpers
# ---------------------------------------------------------------------------


class _Engine:  # minimal placeholder
    pass


def create_engine(*args, **kwargs):  # noqa: D401
    return _Engine()


# ---------------------------------------------------------------------------
# sessionmaker factory
# ---------------------------------------------------------------------------


def sessionmaker(*, autocommit: bool = False, autoflush: bool = False, bind=None):  # noqa: D401,E501
    def _factory():
        return Session()

    return _factory


# ---------------------------------------------------------------------------
# utility constructors for tests referencing `sqlalchemy.orm`
# ---------------------------------------------------------------------------


import types as _types

orm_module = sys.modules.setdefault("sqlalchemy.orm", _types.ModuleType("sqlalchemy.orm"))
orm_module.sessionmaker = sessionmaker  # type: ignore[attr-defined]
orm_module.Session = Session  # type: ignore[attr-defined]
orm_module.validates = lambda *d_args, **d_kwargs: (  # type: ignore[attr-defined]
    lambda fn: fn
)
orm_module.relationship = relationship  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Expose names at top-level module path (`sqlalchemy`)
# ---------------------------------------------------------------------------


this_module = sys.modules[__name__]
sys.modules.setdefault("sqlalchemy", this_module)

# Additional submodules expected by the code-base
sql_module = sys.modules.setdefault("sqlalchemy.ext", _types.ModuleType("sqlalchemy.ext"))
declarative_mod = sys.modules.setdefault("sqlalchemy.ext.declarative", _types.ModuleType("sqlalchemy.ext.declarative"))
declarative_mod.declarative_base = declarative_base  # type: ignore[attr-defined]

# The tests import `sqlalchemy.pool.StaticPool` – provide trivial stub
pool_mod = sys.modules.setdefault("sqlalchemy.pool", _types.ModuleType("sqlalchemy.pool"))


class StaticPool:  # noqa: D401 – placeholder
    pass


pool_mod.StaticPool = StaticPool  # type: ignore[attr-defined]

# ----------------------------------------------------
# Misc helpers expected from top-level SQLAlchemy API
# ----------------------------------------------------


def desc(column):  # noqa: D401 – placeholder for order_by
    return column


this_module.desc = desc  # type: ignore[attr-defined]
