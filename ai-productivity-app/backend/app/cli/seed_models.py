
import asyncio
import json
from pathlib import Path
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.config import ModelConfiguration

MODELS_FIXTURE = Path(__file__).parent / "fixtures" / "models.json"

async def seed_models():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing = await session.execute(select(func.count(ModelConfiguration.id)))
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
