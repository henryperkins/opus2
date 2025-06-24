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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session that is correctly closed afterwards."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Import all models and create their associated tables."""

    # Import models so SQLAlchemy registers them with the metadata.  Some
    # optional components (e.g. *embedding*) require heavy third-party
    # dependencies such as *numpy* that may be unavailable inside the execution
    # sandbox.  Import those lazily within try/except so that the essential
    # core tables are always created even when optional modules cannot be
    # loaded.

    from app.models import (  # noqa: F401  # pylint: disable=unused-import
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

    import sys, os

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

import types as _types


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

    _mod = _types.ModuleType(__name__ + ".transactions")

    @_contextlib.contextmanager  # type: ignore[misc]
    def atomic(session: Session):  # noqa: D401 – identical signature
        """Commit on success / rollback on failure."""

        tx = session.begin()
        try:
            yield session
            tx.commit()
        except Exception:  # pragma: no cover  # noqa: BLE001
            tx.rollback()
            raise

    _mod.atomic = atomic  # type: ignore[attr-defined]

    _sys.modules[_mod.__name__] = _mod
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
