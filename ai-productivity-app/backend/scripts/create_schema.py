"""
Creates all tables in the SQLite DB as defined by current models.Base.

Usage:
    python -m scripts.create_schema
"""

from app.database import engine
from app.models.base import Base

def main():
    print("🔨 Creating all tables using SQLAlchemy models.Base ...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created.")

if __name__ == "__main__":
    main()
