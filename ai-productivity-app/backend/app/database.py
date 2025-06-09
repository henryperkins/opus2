"""Database configuration and session management."""

from typing import Generator

from sqlalchemy import create_engine
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
    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """Return True if a trivial query can be executed successfully."""

    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # pragma: no cover  # noqa: BLE001
        return False
