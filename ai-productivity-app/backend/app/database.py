"""
app/database.py
===============

Engine / session management for both synchronous *and* asynchronous SQLAlchemy
code paths.

Key points
----------
1.  Supports PostgreSQL (psycopg2 OR psycopg-v3) and SQLite (plus aiosqlite).
2.  Downgrades PostgreSQL-only DDL (JSONB, TSVECTOR, exotic CHECK) so models
    compile on SQLite – handy for local tests / CI.
3.  Exposes
        • engine, SessionLocal, get_db()        → synchronous
        • async_engine, AsyncSessionLocal, get_async_db()  → asynchronous
4.  Keeps legacy helpers:  `transactions.atomic`,  `get_engine_sync()`.
5.  Automatically chooses the correct PostgreSQL driver and creates the
    matching async DSN variant (asyncpg / aiosqlite).

This single file covers all persistence needs of the application.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
import types
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import CheckConstraint, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 1.  PostgreSQL → SQLite poly-fills (DDL)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR  # type: ignore

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(_elem, _compiler, **__) -> str:  # noqa: D401
        return "TEXT"

    @compiles(TSVECTOR, "sqlite")
    def _compile_tsvector_sqlite(_elem, _compiler, **__) -> str:  # noqa: D401
        return "TEXT"

except ModuleNotFoundError:
    # PostgreSQL dialect not installed – nothing to do.
    pass


@compiles(CheckConstraint, "sqlite")
def _compile_check_sqlite(element: CheckConstraint, _compiler, **__) -> str:
    """
    Remove operators / functions unsupported by SQLite from CHECK clauses.
    """
    unsupported = ("~", "jsonb_typeof", "char_length")
    text = str(element.sqltext)
    expr = "1" if any(tok in text for tok in unsupported) else element.sqltext
    name = f"CONSTRAINT {element.name} " if element.name else ""
    return f"{name}CHECK ({expr})"


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Helpers – DSN manipulation
# ─────────────────────────────────────────────────────────────────────────────
def _use_psycopg_driver(url: str) -> str:
    """
    Replace `postgresql://` with `postgresql+psycopg://` when psycopg2 is
    missing but psycopg v3 is available.
    """
    if not url.startswith("postgresql://") or "+" in url.split("://", 1)[0]:
        return url

    try:
        import psycopg2  # noqa: F401
        return url
    except ModuleNotFoundError:
        try:
            import psycopg  # noqa: F401
        except ModuleNotFoundError:
            return url
        return url.replace("postgresql://", "postgresql+psycopg://", 1)


def _async_dsn(url: str) -> str:
    """
    Return the asynchronous counterpart of *url*:

        postgresql  → postgresql+asyncpg
        sqlite      → sqlite+aiosqlite
    """
    if url.startswith("sqlite"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")

    if url.startswith("postgresql"):
        dsn = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        pr = urlparse(dsn)
        qs = {k: v for k, v in parse_qsl(pr.query) if k not in {"sslmode", "channel_binding"}}
        return urlunparse(pr._replace(query=urlencode(qs)))

    return url  # unknown – return unchanged


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Synchronous engine & session
# ─────────────────────────────────────────────────────────────────────────────
SYNC_URL = _use_psycopg_driver(settings.database_url)

engine = create_engine(
    SYNC_URL,
    echo=settings.database_echo,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if SYNC_URL.startswith("sqlite") else {},
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autocommit=False, autoflush=False
)

# ─────────────────────────────────────────────────────────────────────────────
# 4.  Asynchronous engine & session
# ─────────────────────────────────────────────────────────────────────────────
ASYNC_URL = _async_dsn(SYNC_URL)

# Ensure the async driver libs are present; fail loudly otherwise
if ASYNC_URL.startswith("sqlite+aiosqlite"):
    __import__("aiosqlite")
elif ASYNC_URL.startswith("postgresql+asyncpg"):
    __import__("asyncpg")

async_engine = create_async_engine(
    ASYNC_URL,
    echo=settings.database_echo,
    pool_pre_ping=True,
    connect_args={"ssl": True} if ASYNC_URL.startswith("postgresql+asyncpg") else {},
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, autoflush=False, autocommit=False
)

# ─────────────────────────────────────────────────────────────────────────────
# 5.  Declarative base
# ─────────────────────────────────────────────────────────────────────────────
Base = declarative_base()

# ─────────────────────────────────────────────────────────────────────────────
# 6.  Dependency helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """Synchronous session – use in background threads or legacy code."""
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to close DB session cleanly: %s", exc)


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async session – preferred for FastAPI endpoints."""
    async with AsyncSessionLocal() as session:
        yield session


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Utility functions
# ─────────────────────────────────────────────────────────────────────────────
def init_db() -> None:
    """
    Import all model modules (side-effect: they register with `Base`) and create
    tables when *not* under pytest.
    """
    import app.models  # noqa: F401  (import triggers model registration)

    if "pytest" not in sys.modules and os.getenv("SKIP_INIT_DB") is None:
        Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """Return True iff `SELECT 1` succeeds on the sync engine."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Legacy shims (transactions.atomic, get_engine_sync) – DO NOT REMOVE
# ─────────────────────────────────────────────────────────────────────────────
def _install_transactions_module() -> None:
    full_name = f"{__name__}.transactions"
    if full_name in sys.modules:
        return

    tx_mod = types.ModuleType(full_name)

    @contextmanager
    def atomic(session: Session):
        """
        Simple `atomic()` context-manager mimicking Django’s behaviour.
        Works for nested calls too.
        """
        if session.in_transaction():
            nested = session.begin_nested()
            try:
                yield session
                nested.commit()
            except Exception:
                nested.rollback()
                raise
        else:
            tx = session.begin()
            try:
                yield session
                tx.commit()
            except Exception:
                tx.rollback()
                raise

    tx_mod.atomic = atomic  # type: ignore[attr-defined]

    sys.modules[full_name] = tx_mod
    setattr(sys.modules[__name__], "transactions", tx_mod)


_install_transactions_module()


def get_engine_sync(*, echo: bool | None = None):  # noqa: D401
    """
    Deprecated helper – returns the global sync engine.
    *echo* arg kept for API compatibility (ignored).
    """
    _ = echo
    return engine
