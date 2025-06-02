"""Minimal database stub for tests.

Provides a `get_db` dependency that yields an in-memory session from the
SQLAlchemy stub as well as `init_db` / `check_db_connection` helpers used by
the (now simplified) application.  All calls are essentially no-ops because
state is fully managed by the in-memory ORM inside `backend/sqlalchemy_stub.py`.
"""

from __future__ import annotations

from backend.sqlalchemy_stub import Session  # noqa: E402 – local import ok


# ---------------------------------------------------------------------------
# Session factory – always returns a new in-memory Session
# ---------------------------------------------------------------------------


def get_db():  # noqa: D401
    db = Session()
    try:
        yield db
    finally:
        pass


# ---------------------------------------------------------------------------
# Compatibility helpers (no-ops)
# ---------------------------------------------------------------------------


def init_db():  # noqa: D401
    return None


def check_db_connection() -> bool:  # noqa: D401
    return True
