# Database connection and session management
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from .config import settings


# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Create engine with appropriate settings
if settings.database_url.startswith("sqlite"):
    # SQLite specific settings for concurrent access
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.database_echo,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

else:
    # PostgreSQL or other databases
    engine = create_engine(
        settings.database_url, pool_pre_ping=True, echo=settings.database_echo
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency to get database session.
    Ensures proper cleanup after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables"""
    from .models import base

    # Import all models to ensure they're registered
    from .models import user, project

    base.Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def check_db_connection() -> bool:
    """Check if database is accessible"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
