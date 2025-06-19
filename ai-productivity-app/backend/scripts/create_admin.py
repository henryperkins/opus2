"""Create or update the initial super-user.

Usage:
    python scripts/create_admin.py --email admin@example.com --password changeme
"""
import argparse
import asyncio
import os
from pathlib import Path
import sys

# ---------------------------------------------------------------------------
# Make sure the project root (the *backend* directory that contains `app/`)
# is available on PYTHONPATH when this script is executed directly
# (e.g. `python scripts/create_admin.py ...`).  Without this, `import app.*`
# will fail because only the `scripts/` folder is added to `sys.path`.
# ---------------------------------------------------------------------------
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.auth.security import hash_password
from app.config import settings   # pydantic settings singleton

parser = argparse.ArgumentParser()
parser.add_argument("--email", required=True)
parser.add_argument("--password", required=True)
parser.add_argument("--non-interactive", action="store_true")

async def create_admin(email: str, password: str) -> None:
    engine = create_async_engine(os.getenv("DATABASE_URL") or settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        existing = await session.scalar(
            User.__table__.select().where(User.email == email)
        )
        if existing:
            print(f"✔ Admin already exists: {existing.email}")
            return

        admin = User(
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        print(f"✅ Created super-user {email}")

def main():
    args = parser.parse_args()
    if not args.non_interactive:
        confirm = input(f"Create admin {args.email}? [y/N] ")
        if confirm.lower() != "y":
            print("Aborted.")
            return
    asyncio.run(create_admin(args.email, args.password))

if __name__ == "__main__":
    main()
