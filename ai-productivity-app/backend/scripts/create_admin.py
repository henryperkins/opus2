"""Create or update the initial super-user.

Usage:
    python scripts/create_admin.py --email admin@example.com --password changeme
"""
import argparse
import asyncio
import os
import sys
import getpass
import re
from pathlib import Path

# Add project root to PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import User
from app.auth.security import hash_password
from app.config import settings

parser = argparse.ArgumentParser()
parser.add_argument("--email", required=True, help="Admin email address")
parser.add_argument("--password", required=False, help="Admin password")
parser.add_argument("--non-interactive", action="store_true", help="Skip confirmation prompt")
parser.add_argument("--update", action="store_true", help="Update existing admin password")


async def create_admin(email: str, password: str, update: bool = False) -> None:
    # Validate inputs
    if "@" not in email or len(email) < 5:
        print("❌ Invalid email format")
        return

    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return

    if not re.search(r"[A-Z]", password) or not re.search(r"\d", password):
        print("❌ Password should contain uppercase and numbers")
        return

    # Get database URL
    db_url = os.getenv("DATABASE_URL") or settings.database_url
    if not db_url:
        print("❌ DATABASE_URL not configured")
        return

    try:
        engine = create_async_engine(db_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Check if admin already exists
            existing = await session.scalar(
                User.__table__.select().where(User.email == email)
            )
            if existing:
                if update:
                    existing.hashed_password = hash_password(password)
                    session.add(existing)
                    await session.commit()
                    print(f"✅ Updated password for admin {email}")
                else:
                    print(f"✔ Admin already exists: {existing.email}")
                return

            # Create new admin
            admin = User(
                email=email,
                hashed_password=hash_password(password),
                is_active=True,
                is_superuser=True,
            )
            session.add(admin)
            await session.commit()
            print(f"✅ Created super-user {email}")

        await engine.dispose()

    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    args = parser.parse_args()

    if not args.password and not args.non_interactive:
        args.password = getpass.getpass("Password: ")

    if not args.non_interactive:
        confirm = input(f"Create admin {args.email}? [y/N] ")
        if confirm.lower() != "y":
            print("Aborted.")
            return

    asyncio.run(create_admin(args.email, args.password, args.update))


if __name__ == "__main__":
    main()
