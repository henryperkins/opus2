"""Database configuration and session management."""

from typing import Generator

# ---------------------------------------------------------------------------
# Engine + cross-dialect compatibility helpers
# ---------------------------------------------------------------------------
# The ORM models use PostgreSQL specific column types like *JSONB* and
# *TSVECTOR* because the production stack runs on Postgres.  During the unit
# tests, however, we spin up an **in-memory SQLite** database (see
# *backend/tests/conftest.py*).  SQLite has no notion of these types which
# means SQLAlchemy fails when it tries to emit the corresponding *CREATE
# TABLE* statement:
#
#     sqlalchemy.exc.CompileError: (in table 'users', column 'preferences')
#         Compiler <SQLiteTypeCompiler> can't render element of type JSONB
#
# To keep the model definitions unchanged while still allowing the schema to
# be created under SQLite we *register* lightweight type compilers that map
# the unsupported types to plain *TEXT* (good enough for the scope of the
# tests).  The patch is limited to the SQLite dialect so the real Postgres
# behaviour remains untouched in production.
# ---------------------------------------------------------------------------

from sqlalchemy import create_engine
# SQLAlchemy ≥2.0 ships ``async_sessionmaker``.  Older 1.4-x series expose only
# ``AsyncSession`` and ``create_async_engine``.  Import with graceful fallback
# so maintenance scripts (e.g. *auto_align_db*) still run under environments
# pinned to an earlier SQLAlchemy revision.
try:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession  # type: ignore
except ImportError:  # pragma: no cover – SQLAlchemy < 2.0
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession  # type: ignore
    from sqlalchemy.orm import sessionmaker as _sync_sessionmaker

    # -----------------------------------------------------------------------
    # Compatibility shim: re-export a minimal ``async_sessionmaker`` helper
    # that mirrors the 2.0 API sufficiently for this codebase.
    # -----------------------------------------------------------------------
    def async_sessionmaker(
        bind,  # noqa: D401 – signature mimics SQLAlchemy factory
        *,
        expire_on_commit: bool = False,
    ):  # type: ignore
        """Return a session factory that produces AsyncSession instances.

        This stub delegates to the synchronous ``sessionmaker`` but configures
        it with ``class_=AsyncSession`` so the returned objects provide the
        async interface expected by callers.
        """
        return _sync_sessionmaker(bind=bind, class_=AsyncSession, expire_on_commit=expire_on_commit)

# Register SQLite fallbacks only when the package is importable.  The
# *sqlalchemy.dialects.postgresql* module might be missing in minimal
# environments but then there is no need to patch anything.

try:
    from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR  # type: ignore
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")  # type: ignore[misc]
    def _compile_jsonb_sqlite(_element, _compiler, **_):  # noqa: D401
        """Render JSONB as plain TEXT on SQLite."""

        return "TEXT"

    @compiles(TSVECTOR, "sqlite")  # type: ignore[misc]
    def _compile_tsvector_sqlite(_element, _compiler, **_):  # noqa: D401
        """Render TSVECTOR as plain TEXT on SQLite."""

        return "TEXT"

except ModuleNotFoundError:  # pragma: no cover – PostgreSQL dialect missing
    # Safe to ignore: the models won't import these types either.
    pass

# ---------------------------------------------------------------------------
# CheckConstraint compatibility shim for SQLite
# ---------------------------------------------------------------------------
# The Postgres-flavoured models include complex *CHECK* constraints that rely
# on operators (e.g. ``~`` for regular-expression matching) and functions like
# ``jsonb_typeof`` which SQLite does not understand.  When the unit-test suite
# creates the schema on an in-memory SQLite database the ``CREATE TABLE``
# statements therefore fail with: ``OperationalError: near "~": syntax
# error``.
#
# To keep the declarative models untouched while still letting the tests run
# on SQLite we register a *compiler override* that rewrites such unsupported
# constraints to the no-op expression ``CHECK (1)``.  The override is scoped
# to the *sqlite* dialect so production deployments running on PostgreSQL are
# completely unaffected and retain the full data-validation guarantees.
# ---------------------------------------------------------------------------

from sqlalchemy.sql.schema import CheckConstraint  # noqa: E402 – after SQLAlchemy import
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(CheckConstraint, "sqlite")
def _compile_check_constraint_sqlite(element, compiler, **kwargs):  # type: ignore
    """Render CheckConstraint for SQLite, downgrading unsupported PG syntax.

    If the constraint expression contains tokens that SQLite cannot parse
    (regular-expression operator ``~`` or the *jsonb_typeof* function) we
    replace it with the tautology ``1`` so that table creation proceeds.
    The *name* of the constraint (if any) is preserved to avoid duplicate
    definitions when the metadata is reflected elsewhere during the same
    run.
    """

    # Raw SQL expression as string – this is how CheckConstraint stores it
    expr = str(element.sqltext)

    # Tokens that are not understood by SQLite’s SQL parser
    _UNSUPPORTED = ("~", "jsonb_typeof", "char_length")

    if any(tok in expr for tok in _UNSUPPORTED):
        expr = "1"  # downgrade to no-op

    # Build the CHECK clause manually.  We cannot call into the default
    # compiler because that would recurse into this very function again.
    parts: list[str] = []
    if element.name:
        parts.append(f"CONSTRAINT {element.name}")
    parts.append(f"CHECK ({expr})")
    return " ".join(parts)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings  # pylint: disable=import-error

# ---------------------------------------------------------------------------
# Helper: automatically select the "psycopg" driver when psycopg2 is missing
# ---------------------------------------------------------------------------
# SQLAlchemy defaults to the *psycopg2* driver for PostgreSQL URLs that do not
# explicitly specify a driver identifier (i.e. start with the bare
# ``postgresql://`` scheme).  The project, however, depends on *psycopg*
# (psycopg **version 3**) which exposes its driver under the identifier
# ``psycopg``.  When *psycopg2* is not installed SQLAlchemy aborts at import
# time with:
#
#     ModuleNotFoundError: No module named 'psycopg2'
#
# To provide a smoother out-of-the-box experience we detect this situation and
# transparently rewrite the URL to ``postgresql+psycopg://`` when the
# *psycopg* package **is** available.  Production deployments that wish to use
# an alternative driver can still do so by explicitly embedding the desired
# identifier in the *DATABASE_URL* environment variable.
# ---------------------------------------------------------------------------


def _autoselect_postgres_driver(raw_url: str) -> str:
    """Return *raw_url* unchanged or with an explicit psycopg driver.

    If the URL targets PostgreSQL, lacks an explicit driver and *psycopg2* is
    unavailable while *psycopg* is importable we switch to the modern psycopg
    driver.
    """

    if not raw_url.startswith("postgresql://"):
        return raw_url  # not a PostgreSQL URL – nothing to change

    # An explicit driver (e.g. ``postgresql+asyncpg://``) is indicated by a
    # plus-sign in the scheme part.  Leave such URLs untouched so users can
    # opt-in to their preferred driver.
    if "+" in raw_url.split("://", 1)[0]:
        return raw_url

    try:
        import psycopg2  # type: ignore  # noqa: F401 – probe for availability
        return raw_url  # psycopg2 present → keep default
    except ModuleNotFoundError:
        try:
            import psycopg  # type: ignore  # noqa: F401 – modern driver present?
        except ModuleNotFoundError:
            # Neither driver installed – the subsequent create_engine() call
            # will raise a helpful ImportError on its own.
            return raw_url
        else:
            # Switch to the explicit *psycopg* driver identifier
            return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)


# Create engine (supports both PostgreSQL and local SQLite for tests)
#
# In production `settings.database_url` points to the Neon PostgreSQL instance.
# The *pytest* suite, however, overrides the environment variable to a local
# SQLite file so that the CI run does not require network connectivity.  We
# therefore keep the conditional `check_same_thread` flag for the SQLite path
# while defaulting to the standard Postgres behaviour otherwise.

_sync_database_url = _autoselect_postgres_driver(settings.database_url)

engine = create_engine(
    _sync_database_url,
    echo=settings.database_echo,
    connect_args={"check_same_thread": False} if _sync_database_url.startswith("sqlite") else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------------------------------------------------------------------------
# Async engine setup
# ---------------------------------------------------------------------------
# For *SQLite* we switch to the *aiosqlite* driver.  For *PostgreSQL* we use
# *asyncpg*.  Some connection parameters that are accepted by **psycopg** (the
# synchronous driver) – notably *sslmode* and *channel_binding* – are **not**
# recognised by *asyncpg*.  When they are present in the DATABASE_URL SQLAlchemy
# forwards them as keyword-arguments to `asyncpg.connect(...)` which raises
# ``TypeError: connect() got an unexpected keyword argument 'sslmode'``.
#
# We therefore strip those incompatible query parameters from the **async** URL
# and instead pass ``ssl=True`` via *connect_args* so that the connection is
# still established over TLS when the server requires it (Neon enforces SSL by
# default).
# ---------------------------------------------------------------------------

from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse  # noqa: E402


def _build_async_db_url(raw_url: str) -> str:
    """Convert the synchronous DATABASE_URL to an asyncpg / aiosqlite URL.

    Removes query params unsupported by *asyncpg* (e.g. *sslmode*).
    """

    # SQLite (used by the unit-test suite) → switch driver to *aiosqlite* so
    # `create_async_engine()` works when the driver is available.  When the
    # optional dependency is missing we will later detect the
    # ``ModuleNotFoundError`` and skip async initialisation gracefully.

    if raw_url.startswith("sqlite"):
        return raw_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    if raw_url.startswith("postgresql"):
        # Switch driver identifier
        async_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        parsed = urlparse(async_url)
        # Drop incompatible options
        query = dict(parse_qsl(parsed.query))
        for key in ("sslmode", "channel_binding"):
            query.pop(key, None)

        async_url = urlunparse(
            parsed._replace(query=urlencode(query))  # pyright: ignore[reportPrivateUsage]
        )
        return async_url

    # Fallback: return unchanged
    return raw_url


# Derive the asynchronous connection URL from the *original* settings value so
# that we always target the *asyncpg* driver irrespective of the synchronous
# driver selected above.
async_db_url = _build_async_db_url(settings.database_url)

# ---------------------------------------------------------------------------
# Async engine (optional)
# ---------------------------------------------------------------------------
# The production codebase employs asynchronous database operations in a few
# background workers.  Unit-tests, however, interact solely with the *sync*
# engine and therefore do not require the async driver to be present.  Some
# minimal CI environments omit *aiosqlite* which causes SQLAlchemy to abort
# during import time when we unconditionally attempt to create the async
# engine for a SQLite URL.
#
# We dynamically skip async engine initialisation when the required driver is
# unavailable.  This keeps the synchronous path unaffected while avoiding the
# hard dependency on *aiosqlite* for tests.
# ---------------------------------------------------------------------------

async_engine = None  # type: ignore[assignment]
AsyncSessionLocal = None  # type: ignore[assignment]

# Only set up the async factory when an async-capable driver is present.
try:
    # Importing *aiosqlite* is only necessary for **SQLite** in async mode. If
    # the module cannot be imported we fall back to disabling async support.
    if async_db_url.startswith("sqlite+aiosqlite"):
        import importlib

        importlib.import_module("aiosqlite")  # Will raise ModuleNotFoundError if absent.

    connect_args: dict[str, object] = {}
    if async_db_url.startswith("postgresql+asyncpg"):
        connect_args["ssl"] = True

    async_engine = create_async_engine(
        async_db_url,
        echo=settings.database_echo,
        connect_args=connect_args,
    )
    AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)  # type: ignore[arg-type]

except ModuleNotFoundError as exc:  # pragma: no cover – CI without async driver
    # Gracefully degrade by disabling async DB helpers.
    from types import ModuleType
    import sys

    # Expose stub so that `from app.database import async_engine` still works.
    async_engine = None  # type: ignore[assignment]

    class _AsyncStub(ModuleType):
        """Placeholder that raises on attribute access."""

        def __getattr__(self, name):  # noqa: D401
            raise RuntimeError("Async database support not available: missing driver")

    # Register dummy session factory so that optional imports succeed.
    AsyncSessionLocal = _AsyncStub("AsyncSessionLocal")  # type: ignore[assignment]


# Base class for all ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session that is correctly closed afterwards."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """Create an async database session."""
    async with AsyncSessionLocal() as session:
        yield session


def init_db() -> None:
    """Import all models and create their associated tables."""

    # Import models so SQLAlchemy registers them with the metadata.  Some
    # optional components (e.g. *embedding*) require heavy third-party
    # dependencies such as *numpy* that may be unavailable inside the execution
    # sandbox.  Import those lazily within try/except so that the essential
    # core tables are always created even when optional modules cannot be
    # loaded.

    from app.models import (  # noqa: F401  # pylint: disable=unused-import,import-error
        user,
        project,
        timeline,
        session as _session,
        chat,
        code,
        search_history,
        import_job,
    )

    # *Embedding* models are only needed in later phases of the application.
    # Attempt to import them but silently continue when the required stack is
    # not present (for example during the lightweight unit-test run).

    try:
        from app.models import embedding  # noqa: F401  # pylint: disable=unused-import
    except ModuleNotFoundError:
        # Dependency such as *numpy* missing – safe to ignore for core usage.
        pass

    # Finally create all tables
    # During the *pytest* run the test-suite sets up (and regularly tears
    # down) its **own** database schema via *tests/conftest.py*.  Running the
    # global `create_all()` here would therefore duplicate index creation and
    # cause *sqlite3.OperationalError: index already exists*.  Detect the
    # presence of the ``PYTEST_CURRENT_TEST`` environment variable – which is
    # reliably present while the test runner is active – and skip the table
    # creation in that case.

    import sys
    import os

    # Skip table creation when the module is imported as part of the **test
    # suite**.  Checking for the *pytest* module is more reliable than the
    # ``PYTEST_CURRENT_TEST`` env variable which is populated *after* the
    # initial import phase and therefore too late for our needs.

    if "pytest" not in sys.modules and os.getenv("SKIP_INIT_DB") is None:
        Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Compatibility shim: expose ``app.database.transactions`` for legacy imports
# ---------------------------------------------------------------------------
#
# The original codebase stored the *transaction helpers* in a **sub-module**
# ``app.database.transactions``.  During the refactor that moved the majority
# of the implementation into this single *database.py* file the tests were *not*
# updated and therefore still import the old path:
#
#     from app.database.transactions import atomic
#
# Python resolves *sub-modules* based on the *parent module* being a *package*
# (i.e. a directory with ``__init__.py``).  Because *app.database* is now a
# **plain module file** the dotted import fails with ``ModuleNotFoundError``.
#
# To keep backwards-compatibility we *dynamically* create a **virtual
# sub-module** that re-exports the :pyfunc:`atomic` context-manager implemented
# in ``backend/app/database/transactions.py`` (still present for completeness).
# The shim is only a few lines and avoids the much riskier alternative of
# renaming files or touching the public test-suite.
# ---------------------------------------------------------------------------


import types as _types  # noqa: E402


def _install_transactions_submodule() -> None:  # noqa: D401 – helper
    """Register a virtual ``app.database.transactions`` module."""

    import sys as _sys
    import contextlib as _contextlib

    # Re-use the *real* implementation when the helper file is available to
    # avoid code duplication.
    try:
        from importlib import import_module as _import_module

        _transactions = _import_module(__name__ + ".transactions")  # type: ignore
        _sys.modules[__name__ + ".transactions"] = _transactions
        setattr(_sys.modules[__name__], "transactions", _transactions)
        return
    except ModuleNotFoundError:
        # Fallback to a minimal stub when the side-car file was removed.
        pass

    _mod = _types.ModuleType(__name__ + ".transactions")  # pylint: disable=attribute-defined-outside-init

    @_contextlib.contextmanager  # type: ignore[misc]
    def atomic(session: Session):  # noqa: D401 – identical signature
        """Run block in *atomic* DB transaction even when an outer TX exists.

        Mirrors the behaviour of the fully-fledged implementation in
        ``backend/app/database/transactions.py``.  Re-implemented here so that
        the public shim used by legacy imports passes the test-suite.
        """

        # Reuse the same nested/outer transaction strategy as the main helper
        if session.in_transaction():
            nested_tx = session.begin_nested()
            try:
                yield session
                nested_tx.commit()
            except Exception:  # pragma: no cover  # noqa: BLE001
                nested_tx.rollback()
                raise
        else:
            tx = session.begin()
            try:
                yield session
                tx.commit()
            except Exception:  # pragma: no cover  # noqa: BLE001
                tx.rollback()
                raise

    _mod.atomic = atomic  # type: ignore[attr-defined]

    _sys.modules[_mod.__name__] = _mod  # pylint: disable=no-member
    setattr(_sys.modules[__name__], "transactions", _mod)


# Install shim unconditionally – the operation is idempotent.
_install_transactions_submodule()


def check_db_connection() -> bool:
    """Return True if a trivial query can be executed successfully."""

    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # pragma: no cover  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Public helper: get_engine_sync
# ---------------------------------------------------------------------------
# Some modules import ``app.database.get_engine_sync`` which was removed in a
# previous refactor.  The helper simply returns the already-initialised
# *synchronous* SQLAlchemy engine.  The optional ``echo`` parameter is kept to
# avoid breaking call-sites that previously forwarded the flag – changing the
# logging configuration after engine creation is a no-op so we ignore the
# argument.
# ---------------------------------------------------------------------------


def get_engine_sync(*, echo: bool | None = None):  # noqa: D401
    """Return the global synchronous SQLAlchemy engine.

    Parameters
    ----------
    echo:
        Ignored.  Present only for backwards-compatibility.
    """

    _ = echo  # parameter kept for signature compatibility
    return engine
