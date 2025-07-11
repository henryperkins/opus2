#!/usr/bin/env python3
"""
Verify that all AI models are properly configured and accessible.
"""
from app.database import SessionLocal
from app.models.config import ModelConfiguration
from sqlalchemy import select


def verify_models():
    """Verify model configuration and availability."""

    with SessionLocal() as session:
        # Get all models
        stmt = select(ModelConfiguration)
        all_models = session.execute(stmt).scalars().all()

        # Get available models
        stmt = select(ModelConfiguration).filter(
            ModelConfiguration.is_available == True
        )
        available_models = session.execute(stmt).scalars().all()

        # Get deprecated models
        stmt = select(ModelConfiguration).filter(
            ModelConfiguration.is_deprecated == True
        )
        deprecated_models = session.execute(stmt).scalars().all()

        print("📊 Model Configuration Status")
        print(f"Total models: {len(all_models)}")
        print(f"Available models: {len(available_models)}")
        print(f"Deprecated models: {len(deprecated_models)}")

        # Count by provider
        providers = {}
        for model in available_models:
            providers[model.provider] = providers.get(model.provider, 0) + 1

        print(f"\nProviders:")
        for provider, count in providers.items():
            print(f"  {provider}: {count} models")

        # Latest models verification
        latest_models = [
            "o4-mini",
            "o3",
            "o3-mini",
            "o3-pro",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4.5",
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-7-sonnet-20250225",
            "claude-3-5-haiku-20241022",
        ]

        available_ids = [m.model_id for m in available_models]

        print(f"\n✅ Latest Models Status:")
        for model_id in latest_models:
            status = "✅" if model_id in available_ids else "❌"
            print(f"  {status} {model_id}")

        # Check capabilities
        reasoning_models = [
            m
            for m in available_models
            if m.capabilities and m.capabilities.get("supports_reasoning")
        ]
        vision_models = [
            m
            for m in available_models
            if m.capabilities and m.capabilities.get("supports_vision")
        ]
        function_models = [
            m
            for m in available_models
            if m.capabilities and m.capabilities.get("supports_functions")
        ]

        print(f"\n🔧 Capabilities:")
        print(f"  Reasoning: {len(reasoning_models)} models")
        print(f"  Vision: {len(vision_models)} models")
        print(f"  Functions: {len(function_models)} models")

        missing_latest = [m for m in latest_models if m not in available_ids]
        if missing_latest:
            print(f"\n❌ Missing models: {missing_latest}")
            return False

        print(f"\n✅ All systems operational!")
        return True


if __name__ == "__main__":
    success = verify_models()
    exit(0 if success else 1)
