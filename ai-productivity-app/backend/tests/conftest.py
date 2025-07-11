"""Test configuration and fixtures."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Always use file-based sqlite DB for tests (guarantees same DB for app and test code)
TEST_DB_PATH = "./test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
# Provide a unique, non-default JWT secret key so that the settings sanity check
# in `app.config` does not abort the application startup during the test run.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
from app.main import app
from app.database import get_db
from app.models.base import Base

# Remove previous test DB
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Set up the test database tables at the start of the session, and drop at the end."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Clean up database state between tests to avoid cross-test contamination
        # Drop all data and recreate tables so unique constraints do not fail when
        # fixtures insert records with identical primary/unique keys in separate
        # tests. Using drop/create instead of DELETE for performance on the small
        # SQLite test DB.
        from app.models.base import Base  # local import to avoid circular deps

        # Drop and recreate all tables to ensure a pristine state for the next test
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
# Some test modules (e.g. *test_atomic_transactions.py*) rely on ``test_user``
# and ``test_project`` fixtures that were originally defined *locally* in other
# test files.  When Pytest does not collect those provider modules (for
# instance when the user runs a subset of the suite) the fixtures are missing
# which results in a *"fixture 'test_user' not found"* error.  Moving the
# definitions into *conftest.py* makes them available globally without having
# to touch every individual test.

from app.models.user import (
    User,
)  # noqa: E402 – imported late to avoid heavy deps at import time
from app.models.project import Project  # noqa: E402


@pytest.fixture()
def test_user(db):  # type: ignore
    """Return a persisted *User* record for tests that need an authenticated user."""

    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashedpassword",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def test_project(db, test_user):  # type: ignore
    """Return a persisted *Project* owned by the *test_user* fixture."""

    project = Project(
        title="Test Project",
        description="A test project",
        owner_id=test_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------------------------
# Async variants required by *test_feedback_integration.py* and others
# ---------------------------------------------------------------------------

# The feedback integration tests exercise the *async* router stack using
# ``httpx.AsyncClient`` and therefore require asynchronous fixtures that are
# not part of the original test harness which only exposed *synchronous* DB
# and client helpers.  Adding lightweight wrappers here avoids code
# duplication across multiple test modules while keeping the synchronous
# fixtures intact for existing tests that rely on them.

import asyncio  # noqa: E402 – imported late on purpose
from httpx import AsyncClient  # noqa: E402

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402


@pytest.fixture()
async def test_session() -> AsyncSession:  # type: ignore
    """Provide an *AsyncSession* against the same SQLite file as the sync DB.

    The synchronous fixture above already created all tables via the sync
    engine.  SQLite shares the underlying file between connections which means
    we can safely reuse the schema for the async engine.  Each test gets its
    own independent transaction that is rolled back afterwards to guarantee a
    pristine state.
    """

    async with AsyncSessionLocal() as session:  # type: ignore
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture()
async def async_client(test_session):  # noqa: D401 – pytest fixture
    """FastAPI test client that speaks HTTP/1.1 over *async* interfaces."""

    from app.main import app  # imported lazily to avoid heavy startup cost
    from app.database import get_db as _sync_get_db

    # Override the synchronous `get_db` dependency with an async variant that
    # yields the *AsyncSession* from the `test_session` fixture created above.
    async def _override_get_db():  # type: ignore
        yield test_session

    app.dependency_overrides[_sync_get_db] = _override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:  # type: ignore[attr-defined]
        yield client

    # Clean-up so other tests that rely on the synchronous `client` fixture do
    # not accidentally receive the async override.
    app.dependency_overrides.pop(_sync_get_db, None)
