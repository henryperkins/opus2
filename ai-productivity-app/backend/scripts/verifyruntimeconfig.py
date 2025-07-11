import os
import sys
import json
from datetime import datetime

# Add backend to path - handle both local and Docker environments
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(script_dir, '..')
if '/app/scripts' in script_dir:
    # Running in Docker container
    backend_path = '/app'
sys.path.insert(0, backend_path)

from app.database import SessionLocal
from app.models.config import RuntimeConfig, ConfigHistory
from sqlalchemy import func

def verify_runtime_config():
    """Verify runtime configuration in the database."""

    # Use the app's database connection
    with SessionLocal() as session:
        # Count total configs
        total_count = session.query(func.count(RuntimeConfig.key)).scalar()
        print(f"\n📊 Total runtime configs in database: {total_count}")

        if total_count == 0:
            print("❌ No runtime configuration found!")
            print("\n💡 This might be normal if the app just started.")
            print("   Default configuration will be created on first API call.")
            return

        # Get all configs
        configs = session.query(RuntimeConfig).order_by(RuntimeConfig.key).all()

        print("\n🔧 Current Runtime Configuration:")
        print("=" * 80)
        print(f"{'Key':<30} {'Type':<10} {'Value':<30} {'Updated By':<15}")
        print("-" * 80)

        for config in configs:
            value_str = str(config.value)
            if len(value_str) > 30:
                value_str = value_str[:27] + "..."

            print(f"{config.key:<30} {config.value_type:<10} {value_str:<30} {config.updated_by or 'system':<15}")

        # Try to reconstruct the unified config
        print("\n🔄 Reconstructed Unified Config:")
        print("=" * 80)

        config_dict = {}
        for config in configs:
            try:
                if config.value_type == "boolean":
                    config_dict[config.key] = config.value in (True, "true", "True", "1", 1)
                elif config.value_type == "number":
                    config_dict[config.key] = config.value
                elif config.value_type in ("object", "array"):
                    config_dict[config.key] = config.value
                else:
                    config_dict[config.key] = str(config.value)
            except Exception as e:
                print(f"❌ Error parsing {config.key}: {e}")

        # Pretty print the config
        print(json.dumps(config_dict, indent=2, sort_keys=True))

        # Check config history
        history_count = session.query(func.count(ConfigHistory.config_key)).scalar()
        if history_count > 0:
            print(f"\n📜 Configuration History: {history_count} changes")
            print("=" * 80)

            # Get last 10 changes
            recent_changes = session.query(ConfigHistory).order_by(
                ConfigHistory.changed_at.desc()
            ).limit(10).all()

            for change in recent_changes:
                print(f"\n🕐 {change.changed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Key: {change.config_key}")
                print(f"   Changed by: {change.changed_by}")
                print(f"   Old value: {change.old_value}")
                print(f"   New value: {change.new_value}")
        else:
            print("\n📜 No configuration history found")

        # Check for common issues
        print("\n⚠️  Configuration Analysis:")
        print("=" * 80)

        # Check if model_id exists and is valid
        model_id_config = next((c for c in configs if c.key == "model_id"), None)
        if model_id_config:
            print(f"✅ model_id is configured: {model_id_config.value}")

            # Check if this model exists in ModelConfiguration
            from app.models.config import ModelConfiguration
            model = session.query(ModelConfiguration).filter_by(
                model_id=model_id_config.value
            ).first()

            if model:
                print(f"✅ Model '{model_id_config.value}' exists in ModelConfiguration table")
                print(f"   Provider: {model.provider}")
                print(f"   Available: {model.is_available}")
            else:
                print(f"❌ Model '{model_id_config.value}' NOT FOUND in ModelConfiguration table!")
        else:
            print("❌ model_id is not configured in RuntimeConfig")

        # Check provider
        provider_config = next((c for c in configs if c.key == "provider"), None)
        if provider_config:
            print(f"\n✅ provider is configured: {provider_config.value}")
        else:
            print("\n❌ provider is not configured in RuntimeConfig")

if __name__ == "__main__":
    verify_runtime_config()
