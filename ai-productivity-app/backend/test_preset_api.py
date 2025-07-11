"""Debug script to test preset API endpoint"""

import requests
import json

# Test the preset endpoint
response = requests.get("http://localhost:8000/api/v1/ai-config/presets")

if response.status_code == 200:
    presets = response.json()
    print("Presets from API:")
    print("=" * 50)
    
    for preset in presets:
        print(f"\nPreset: {preset['name']} ({preset['id']})")
        print(f"Description: {preset['description']}")
        print(f"Config:")
        print(json.dumps(preset['config'], indent=2))
        
        # Check if provider is included
        if 'provider' not in preset['config']:
            print("  ⚠️  WARNING: Provider field is missing!")
        else:
            print(f"  ✓ Provider is included: {preset['config']['provider']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
