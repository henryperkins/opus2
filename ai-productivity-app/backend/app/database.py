"""
Database engine / session management.

Highlights
----------
• Supports PostgreSQL (psycopg, asyncpg) and SQLite (incl. aiosqlite for tests).
• Patches PG-only column types (JSONB, TSVECTOR) and complex CHECK constraints
  so models can be created on SQLite unchanged.
• Transparently swaps to the ‘psycopg’ driver when psycopg2 is missing.
• Exposes synchronous and *optional* asynchronous engines & session factories.
• Ships several shims for legacy import paths still used by old test-code.
"""

from __future__ import annotations

import os
import sys
import types
from contextlib import contextmanager
from typing import Generator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.schema import CheckConstraint

from app.config import settings

# --------------------------------------------------------------------------- #
# Async helpers – SQLAlchemy ≥2.0 / 1.4 fallback                               #
# --------------------------------------------------------------------------- #
try:  # ≥ 2.0
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
except ImportError:  # 1.4 poly-fill
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker as _sync_sessionmaker

    def async_sessionmaker(bind, *, expire_on_commit: bool = False):  # type: ignore
        """Minimal replacement for SQLAlchemy ≥2.0 async_sessionmaker()."""
        return _sync_sessionmaker(
            bind=bind, class_=AsyncSession, expire_on_commit=expire_on_commit
        )


# --------------------------------------------------------------------------- #
# Module-level logger
# --------------------------------------------------------------------------- #
logger = logging.getLogger(__name__)
# --------------------------------------------------------------------------- #
# 1. SQLite compilers – PG types & CHECK constraints                           #
# --------------------------------------------------------------------------- #
try:
    from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR  # type: ignore

    @compiles(JSONB, "sqlite")
    def _jsonb_sqlite(_elem, _comp, **_) -> str:  # noqa: D401
        return "TEXT"

    @compiles(TSVECTOR, "sqlite")
    def _tsvector_sqlite(_elem, _comp, **_) -> str:  # noqa: D401
        return "TEXT"

except ModuleNotFoundError:  # dialect not installed
    pass


@compiles(CheckConstraint, "sqlite")
def _check_sqlite(element, _comp, **_) -> str:  # type: ignore
    """Strip PG-specific operators/functions from CHECK for SQLite."""
    unsupported = ("~", "jsonb_typeof", "char_length")
    expr = (
        "1"
        if any(tok in str(element.sqltext) for tok in unsupported)
        else element.sqltext
    )
    name = f"CONSTRAINT {element.name} " if element.name else ""
    return f"{name}CHECK ({expr})"


# --------------------------------------------------------------------------- #
# 2. URL helpers                                                              #
# --------------------------------------------------------------------------- #
def _autoselect_postgres_driver(url: str) -> str:
    """Add ‘+psycopg’ when psycopg2 is absent but psycopg (v3) is present."""
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


def _build_async_url(url: str) -> str:
    """Return async-capable variant of *url* (asyncpg / aiosqlite)."""
    if url.startswith("sqlite"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")

    if url.startswith("postgresql"):
        async_url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        parsed = urlparse(async_url)
        qs = {
            k: v
            for k, v in parse_qsl(parsed.query)
            if k not in {"sslmode", "channel_binding"}
        }
        return urlunparse(parsed._replace(query=urlencode(qs)))  # pyright: ignore

    return url


# --------------------------------------------------------------------------- #
# Legacy helper – alias for backward compatibility                            #
# --------------------------------------------------------------------------- #
# Some modules (e.g., app.embeddings.worker) still import the historical
# `_build_async_db_url` symbol.  Provide a thin alias to the new helper to
# avoid breaking older import paths without duplicating logic.
_build_async_db_url = _build_async_url
# --------------------------------------------------------------------------- #
# 3. Synchronous engine & session                                             #
# --------------------------------------------------------------------------- #
_sync_url = _autoselect_postgres_driver(settings.database_url)

engine = create_engine(
    _sync_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _sync_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# --------------------------------------------------------------------------- #
# 4. Optional asynchronous engine & session                                   #
# --------------------------------------------------------------------------- #
async_engine = None  # type: ignore
AsyncSessionLocal = None  # type: ignore

_async_url = _build_async_url(settings.database_url)
try:
    # SQLite async → verify aiosqlite exists
    if _async_url.startswith("sqlite+aiosqlite"):
        __import__("aiosqlite")

    connect_args: dict[str, object] = (
        {"ssl": True} if _async_url.startswith("postgresql+asyncpg") else {}
    )

    async_engine = create_async_engine(
        _async_url,
        echo=settings.database_echo,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)  # type: ignore[arg-type]

except ModuleNotFoundError:  # driver missing – expose stub

    class _AsyncStub(types.ModuleType):
        def __getattr__(self, _):
            raise RuntimeError("Async DB support unavailable – missing driver")

    AsyncSessionLocal = _AsyncStub("AsyncSessionLocal")  # type: ignore


# --------------------------------------------------------------------------- #
# 5. Public helpers                                                           #
# --------------------------------------------------------------------------- #
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a synchronous DB session and ensure safe cleanup.

    Rollback/close operations can raise when the underlying connection
    has already been terminated (e.g. client disconnect during WebSocket).
    We catch and log these errors instead of letting them bubble up and
    pollute the ASGI exception logs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception as exc:  # pragma: no cover – defensive catch
            # Avoid cascading errors when the connection is already closed
            logger.warning("Failed to close DB session cleanly: %s", exc)


async def get_async_db() -> Generator[AsyncSession, None, None]:  # type: ignore[name-defined]
    async with AsyncSessionLocal() as session:  # type: ignore[attr-defined]
        yield session


def init_db() -> None:
    """Import models and create tables unless running under pytest."""
    # Core models
    from app.models import (  # noqa: F401
        chat,
        code,
        import_job,
        project,
        search_history,
        session as _session,
        timeline,
        user,
    )

    # Optional embedding
    try:
        from app.models import embedding  # noqa: F401
    except ModuleNotFoundError:
        pass

    if "pytest" not in sys.modules and os.getenv("SKIP_INIT_DB") is None:
        Base.metadata.create_all(bind=engine)


# --------------------------------------------------------------------------- #
# 6. Legacy sub-module shim: app.database.transactions                        #
# --------------------------------------------------------------------------- #
def _install_transactions_submodule() -> None:
    """Expose a minimal ‘app.database.transactions’ for old imports."""
    import importlib

    full_name = f"{__name__}.transactions"
    try:
        module = importlib.import_module(full_name)
    except ModuleNotFoundError:
        module = types.ModuleType(full_name)

        @contextmanager
        def atomic(session: Session):
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

        module.atomic = atomic  # type: ignore[attr-defined]

    sys.modules[full_name] = module
    setattr(sys.modules[__name__], "transactions", module)


_install_transactions_submodule()


# --------------------------------------------------------------------------- #
# 7. Misc. convenience functions                                              #
# --------------------------------------------------------------------------- #
def check_db_connection() -> bool:
    """Return True when ‘SELECT 1’ succeeds."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False


def get_engine_sync(*, echo: bool | None = None):  # noqa: D401
    """Legacy alias – returns the global sync engine (echo ignored)."""
    _ = echo
    return engine
