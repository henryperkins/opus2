import os
import sys
from datetime import datetime

# Add backend to path - handle both local and Docker environments
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(script_dir, '..')
if '/app/scripts' in script_dir:
    # Running in Docker container
    backend_path = '/app'
elif 'backend/scripts' in script_dir:
    # Running locally
    backend_path = os.path.join(script_dir, '..')
sys.path.insert(0, backend_path)

from app.database import SessionLocal
from app.models.config import ModelConfiguration
from sqlalchemy import func

def verify_models():
    """Verify models are properly seeded in the database."""

    # Use the app's database connection
    with SessionLocal() as session:
        # Count total models
        total_count = session.query(func.count(ModelConfiguration.model_id)).scalar()
        print(f"\n📊 Total models in database: {total_count}")

        if total_count == 0:
            print("❌ No models found in database!")
            return

        # Get all models
        all_models = session.query(ModelConfiguration).order_by(
            ModelConfiguration.provider,
            ModelConfiguration.model_id
        ).all()

        # Group by provider
        providers = {}
        for model in all_models:
            if model.provider not in providers:
                providers[model.provider] = []
            providers[model.provider].append(model)

        # Display models by provider
        print("\n📋 Models by Provider:")
        print("=" * 80)

        for provider, models in sorted(providers.items()):
            print(f"\n🏢 {provider.upper()} ({len(models)} models)")
            print("-" * 40)

            for model in models:
                status = "✅" if model.is_available else "❌"
                deprecated = " (DEPRECATED)" if model.is_deprecated else ""
                print(f"  {status} {model.model_id:<30} - {model.name}{deprecated}")

                # Show key details
                if model.is_available:
                    print(f"     Family: {model.model_family}")
                    print(f"     Context: {model.context_window:,} tokens")
                    if model.max_tokens:
                        print(f"     Max Output: {model.max_tokens:,} tokens")
                    if model.cost_input_per_1k:
                        print(f"     Cost: ${model.cost_input_per_1k:.4f} input / ${model.cost_output_per_1k:.4f} output per 1k tokens")

                    # Show capabilities
                    caps = model.capabilities or {}
                    cap_list = []
                    if caps.get('supports_streaming'): cap_list.append("streaming")
                    if caps.get('supports_functions'): cap_list.append("functions")
                    if caps.get('supports_vision'): cap_list.append("vision")
                    if caps.get('supports_reasoning'): cap_list.append("reasoning")
                    if caps.get('supports_thinking'): cap_list.append("thinking")
                    if cap_list:
                        print(f"     Capabilities: {', '.join(cap_list)}")
                    print()

        # Summary statistics
        print("\n📈 Summary Statistics:")
        print("=" * 80)

        available_count = session.query(func.count(ModelConfiguration.model_id)).filter(
            ModelConfiguration.is_available == True
        ).scalar()

        deprecated_count = session.query(func.count(ModelConfiguration.model_id)).filter(
            ModelConfiguration.is_deprecated == True
        ).scalar()

        print(f"Total models: {total_count}")
        print(f"Available models: {available_count}")
        print(f"Deprecated models: {deprecated_count}")

        # Check specific models mentioned in logs
        print("\n🔍 Checking specific models from logs:")
        print("=" * 80)

        expected_models = [
            "o4-mini", "o3", "o3-mini", "o3-pro",
            "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4.5",
            "gpt-4o-mini", "gpt-4o", "o1-preview", "o1-mini",
            "claude-opus-4-20250514", "claude-sonnet-4-20250514",
            "claude-3-7-sonnet-20250225", "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", "gpt-3.5-turbo"
        ]

        for model_id in expected_models:
            model = session.query(ModelConfiguration).filter_by(model_id=model_id).first()
            if model:
                print(f"✅ {model_id} - Found (Provider: {model.provider})")
            else:
                print(f"❌ {model_id} - NOT FOUND")

        # Check for any issues
        print("\n⚠️  Potential Issues:")
        print("=" * 80)

        # Models without providers
        no_provider = session.query(ModelConfiguration).filter(
            (ModelConfiguration.provider == None) | (ModelConfiguration.provider == "")
        ).all()
        if no_provider:
            print(f"❌ Models without provider: {len(no_provider)}")
            for m in no_provider:
                print(f"   - {m.model_id}")

        # Models without names
        no_name = session.query(ModelConfiguration).filter(
            (ModelConfiguration.name == None) | (ModelConfiguration.name == "")
        ).all()
        if no_name:
            print(f"❌ Models without name: {len(no_name)}")
            for m in no_name:
                print(f"   - {m.model_id}")

        if not no_provider and not no_name:
            print("✅ All models have required fields")

if __name__ == "__main__":
    verify_models()
