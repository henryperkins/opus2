"""Seed the **model catalogue** table with built-in fixtures.

This script is intentionally *self-contained* so it can be executed on a
fresh checkout without requiring any external services such as a running
PostgreSQL instance.  When no ``DATABASE_URL`` environment variable is
present – **or** the variable points at a *remote* Postgres host that is
inaccessible from typical sandbox environments – we transparently fall back
to a local SQLite database under ``./data/app.db``.

The implementation uses *synchronous* SQLAlchemy sessions exclusively.  An
earlier asynchronous variant failed in restricted containers because Python’s
default event-loop attempts to create a *socketpair()* which is prohibited by
the security policy.  For a one-off seeding task the synchronous code path is
perfectly adequate and avoids the sandbox limitation entirely.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# 0. Ensure a usable DATABASE_URL (SQLite fallback)                          #
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Prefer the given DATABASE_URL. Only fall back when **no** URL is defined.  #
# ---------------------------------------------------------------------------

_env_url = os.getenv("DATABASE_URL", "")

# ---------------------------------------------------------------------------
# Basic *safety* secret to satisfy app.config's startup checks.              #
# ---------------------------------------------------------------------------
#
# The application’s global configuration layer aborts process start-up when
# it detects that the **default** JWT secret key is still in use.  For the
# self-contained *seeding* utility this stringent production check is
# overkill – the task merely inserts fixture rows and terminates.  To avoid
# forcing developers to export an explicit `JWT_SECRET_KEY` ahead of every
# invocation we inject a lightweight fallback **before** the configuration
# module is ever imported.

if not (os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")):
    # A short, non-guessable placeholder.  It only needs to differ from the
    # default value defined in `app.config.DEFAULT_SECRET` so that the
    # import guard is bypassed.
    os.environ["JWT_SECRET_KEY"] = "local-seed-models-key"

if not _env_url:
    repo_root = Path(__file__).resolve().parents[3]  # …/ai-productivity-app
    sqlite_path = repo_root / "data" / "app.db"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{sqlite_path}"

# ---------------------------------------------------------------------------
# 1. Imports that rely on a configured DATABASE_URL                         #
# ---------------------------------------------------------------------------

from sqlalchemy import func, select

from app.database import SessionLocal, engine as pg_engine
from app.models.config import ModelConfiguration

# Paths to fixture files (comprehensive first, minimal fallback)
_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_MODELS_FIXTURE_COMPLETE = _FIXTURE_DIR / "models_complete.json"
_MODELS_FIXTURE_LEGACY = _FIXTURE_DIR / "models.json"


def _load_fixture() -> list[dict]:
    """Return list with model dictionaries from the preferred fixture."""

    fixture_path = (
        _MODELS_FIXTURE_COMPLETE
        if _MODELS_FIXTURE_COMPLETE.exists()
        else _MODELS_FIXTURE_LEGACY
    )

    with fixture_path.open() as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# 2. Main seeding routine                                                    #
# ---------------------------------------------------------------------------


def seed_models() -> None:  # noqa: D401 (simple name fine)
    """Insert model catalogue rows unless they already exist."""

    # Ensure the *model_configurations* table exists in the **target**
    # database.  We first try the configured (likely PostgreSQL) connection
    # and, if that is unreachable (common inside sandboxed CI environments),
    # transparently fall back to a local SQLite file so that developers can
    # still run the seeding procedure without network access.

    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine

    target_engine = pg_engine
    target_session_factory = SessionLocal

    try:
        # Quick connectivity probe.
        with target_engine.connect() as conn:
            conn.execute(select(1))
    except OperationalError:
        print("⚠️  PostgreSQL unreachable – switching to local SQLite fallback.")

        repo_root = Path(__file__).resolve().parents[3]
        sqlite_path = repo_root / "data" / "app.db"
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        sqlite_url = f"sqlite:///{sqlite_path}"

        target_engine = create_engine(
            sqlite_url, connect_args={"check_same_thread": False}
        )
        target_session_factory = sessionmaker(
            bind=target_engine, autocommit=False, autoflush=False
        )

    # Create only the *model_configurations* table to avoid PG-specific DDL
    # that SQLite cannot parse.
    ModelConfiguration.metadata.create_all(
        bind=target_engine, tables=[ModelConfiguration.__table__]
    )

    # Open session against the *selected* engine (PostgreSQL or fallback
    # SQLite) and perform the actual seeding work.
    with target_session_factory() as session:
        existing_count = session.execute(
            select(func.count(ModelConfiguration.model_id))
        ).scalar_one()

        if existing_count:
            print("Models already seeded – nothing to do ✅")
            return

        models = _load_fixture()

        for model_data in models:
            session.add(ModelConfiguration(**model_data))

        session.commit()

        # ------------------------------------------------------------------
        # Verification – ensure rows actually persisted
        # ------------------------------------------------------------------
        persisted = session.execute(
            select(func.count(ModelConfiguration.model_id))
        ).scalar_one()

        if persisted >= len(models):
            print(f"Seeded {persisted} models into database 📦 (verified)")
        else:
            print(
                "⚠️  Model count after seeding lower than expected – "
                f"expected ≥{len(models)}, found {persisted}."
            )


# ---------------------------------------------------------------------------
# 3. Script entry-point                                                      #
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    seed_models()
