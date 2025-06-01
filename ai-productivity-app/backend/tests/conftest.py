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
