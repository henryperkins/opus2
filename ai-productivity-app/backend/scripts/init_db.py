"""
Initialize database with baseline data.

Usage:
    python -m scripts.init_db
"""
import asyncio
import sys
from pathlib import Path

# Ensure project root (backend) is importable when script executed directly
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.auth.security import hash_password  # noqa: E402


async def seed() -> None:
    """
    Idempotently create an initial super-user so fresh environments
    have an account to log in with.
    """
    db = SessionLocal()
    try:
        admin_email = "admin@example.com"
        admin_password = "changeme"

        existing = db.query(User).filter_by(email=admin_email).first()
        if existing:
            print(f"✔ Admin already exists: {existing.email}")
            return

        admin = User(
            username="admin",
            email=admin_email,
            password_hash=hash_password(admin_password),
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"✅ Created super-user {admin_email}")
    finally:
        db.close()


def main() -> None:
    print("🗄️ Initializing database...")
    init_db()
    print("✅ Database schema created")
    asyncio.run(seed())


if __name__ == "__main__":
    main()
