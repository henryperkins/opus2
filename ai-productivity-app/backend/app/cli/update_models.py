#!/usr/bin/env python3
"""
Update the model configuration database with the latest models.

This script will:
1. Load the latest models from the fixtures file
2. Update existing models with new information
3. Add new models that don't exist
4. Mark deprecated models as such

Usage:
    python -m app.cli.update_models
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.config import ModelConfiguration

# Load models from the comprehensive fixture
MODELS_FIXTURE_COMPLETE = Path(__file__).parent / "fixtures" / "models_complete.json"


def parse_datetime(dt_str: str) -> datetime:
    """Simple datetime parser for ISO format strings."""
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    return datetime.fromisoformat(dt_str)


async def update_models():
    """Update the model configuration database with latest models."""
    async with AsyncSessionLocal() as session:
        # Load fixture data
        if not MODELS_FIXTURE_COMPLETE.exists():
            print(f"Error: Fixture file not found: {MODELS_FIXTURE_COMPLETE}")
            return

        with open(MODELS_FIXTURE_COMPLETE) as f:
            fixture_models = json.load(f)

        print(f"Loading {len(fixture_models)} models from fixture...")

        # Get all existing models
        existing_models = await session.execute(select(ModelConfiguration))
        existing_models_dict = {
            model.model_id: model for model in existing_models.scalars().all()
        }

        print(f"Found {len(existing_models_dict)} existing models in database")

        # Track changes
        added = 0
        updated = 0
        deprecated = 0

        # Process each model from fixture
        for model_data in fixture_models:
            model_id = model_data["model_id"]

            if model_id in existing_models_dict:
                # Update existing model
                existing_model = existing_models_dict[model_id]

                # Update all fields
                for field, value in model_data.items():
                    if hasattr(existing_model, field):
                        # Handle datetime fields
                        if field == "deprecated_at" and isinstance(value, str):
                            value = parse_datetime(value) if value else None
                        setattr(existing_model, field, value)

                existing_model.updated_at = datetime.utcnow()
                updated += 1
                print(f"Updated: {model_id}")
            else:
                # Add new model
                # Handle deprecated_at field
                if "deprecated_at" in model_data and isinstance(
                    model_data["deprecated_at"], str
                ):
                    model_data["deprecated_at"] = parse_datetime(
                        model_data["deprecated_at"]
                    )
                elif (
                    model_data.get("is_deprecated", False)
                    and "deprecated_at" not in model_data
                ):
                    model_data["deprecated_at"] = datetime.utcnow()

                new_model = ModelConfiguration(**model_data)
                session.add(new_model)
                added += 1
                print(f"Added: {model_id}")

        # Mark models not in fixture as deprecated (optional)
        fixture_model_ids = {model["model_id"] for model in fixture_models}
        for model_id, existing_model in existing_models_dict.items():
            if model_id not in fixture_model_ids and not existing_model.is_deprecated:
                existing_model.is_deprecated = True
                existing_model.deprecated_at = datetime.utcnow()
                deprecated += 1
                print(f"Deprecated: {model_id}")

        # Commit changes
        await session.commit()

        print(f"\nModel update complete:")
        print(f"  Added: {added}")
        print(f"  Updated: {updated}")
        print(f"  Deprecated: {deprecated}")
        print(f"  Total models: {len(fixture_models)}")


if __name__ == "__main__":
    asyncio.run(update_models())
