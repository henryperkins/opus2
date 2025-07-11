"""Test script to verify preset configurations include provider field"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.database import SessionLocal
from app.services.config_preset_manager import ConfigPresetManager

# Create a session
db = SessionLocal()

try:
    # Create preset manager
    preset_manager = ConfigPresetManager(db)
    
    # Get all presets
    presets = preset_manager.get_presets()
    
    print("Available presets:")
    print("=" * 50)
    
    for preset in presets:
        print(f"\nPreset: {preset['name']} ({preset['id']})")
        print(f"Description: {preset['description']}")
        print(f"Config:")
        for key, value in preset['config'].items():
            print(f"  {key}: {value}")
        
        # Check if provider is included
        if 'provider' not in preset['config']:
            print("  WARNING: Provider field is missing!")
        else:
            print(f"  ✓ Provider is included: {preset['config']['provider']}")
    
finally:
    db.close()
