"""Test the complete preset flow"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.database import SessionLocal
from app.schemas.generation import ConfigUpdate, UnifiedModelConfig
from app.services.unified_config_service import UnifiedConfigService
import json

# Test data that mimics what the frontend is sending for "powerful" preset
preset_data = {
    "enableReasoning": True,
    "maxTokens": 4096,
    "modelId": "gpt-4o",
    "reasoningEffort": "high",
    "temperature": 0.7
}

print("Testing preset application flow")
print("=" * 50)
print("\n1. Frontend sends this preset data:")
print(json.dumps(preset_data, indent=2))

try:
    # Step 1: Create ConfigUpdate from frontend data
    print("\n2. Creating ConfigUpdate...")
    update = ConfigUpdate(**preset_data)
    print("✓ ConfigUpdate created successfully")
    print(f"   Parsed fields: {update.dict(exclude_unset=True)}")
    
    # Step 2: Test the update process
    print("\n3. Applying update to current config...")
    db = SessionLocal()
    service = UnifiedConfigService(db)
    
    # Get current config
    current = service.get_current_config()
    print(f"   Current provider: {current.provider}")
    print(f"   Current model: {current.model_id}")
    
    # Try to apply the update
    print("\n4. Attempting to update config...")
    try:
        # Convert to dict format expected by update_config
        update_dict = update.dict(exclude_unset=True)
        print(f"   Update dict: {update_dict}")
        
        new_config = service.update_config(update_dict, updated_by="test")
        print("✓ Update successful!")
        print(f"   New provider: {new_config.provider}")
        print(f"   New model: {new_config.model_id}")
    except ValueError as e:
        print(f"✗ Update failed with ValueError: {e}")
        
        # Try to understand the error better
        if "Field required" in str(e):
            print("\n   This is the 'Field required' error!")
            print("   Likely missing fields when creating UnifiedModelConfig")
            
            # Let's try to manually create the merged config to see what's missing
            print("\n5. Debugging merged config...")
            merged = current.model_dump()
            merged.update(update_dict)
            print(f"   Merged config keys: {list(merged.keys())}")
            print(f"   Provider in merged: {'provider' in merged}")
            print(f"   Model_id in merged: {'model_id' in merged}")
            
            # Try to create UnifiedModelConfig directly
            try:
                test_config = UnifiedModelConfig(**merged)
                print("   ✓ UnifiedModelConfig creation would succeed")
            except Exception as e2:
                print(f"   ✗ UnifiedModelConfig creation fails: {e2}")
                if hasattr(e2, 'errors'):
                    for error in e2.errors():
                        print(f"     - {error}")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if 'db' in locals():
        db.close()
