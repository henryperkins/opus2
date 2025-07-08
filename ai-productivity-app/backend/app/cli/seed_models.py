
import asyncio
import json
from pathlib import Path
"""Seed the **model catalogue** table with a built-in fixtures file.

The script is designed to be idempotent – running it multiple times will not
create duplicates thanks to the *primary-key* constraint on ``model_id``.
"""

from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.config import ModelConfiguration

MODELS_FIXTURE = Path(__file__).parent / "fixtures" / "models.json"

async def seed_models():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        # Use the correct primary-key column for the count check.
        # ``ModelConfiguration`` defines ``model_id`` as the primary key –
        # there is no generic ``id`` column. Referencing the non-existent
        # attribute raised an ``AttributeError`` which bubbled up to the
        # startup routine and caused model seeding to be skipped.
        existing = await session.execute(select(func.count(ModelConfiguration.model_id)))
        if existing.scalar() > 0:
            print("Models already seeded")
            return
        
        # Load fixture
        with open(MODELS_FIXTURE) as f:
            models = json.load(f)
        
        # Insert models
        for model_data in models:
            model = ModelConfiguration(**model_data)
            session.add(model)
        
        await session.commit()
        print(f"Seeded {len(models)} models")

if __name__ == "__main__":
    asyncio.run(seed_models())
