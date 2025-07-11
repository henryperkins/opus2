# Quick script to test ConfigUpdate validation
from app.schemas.generation import ConfigUpdate
import json

# Test data that mimics what the frontend is sending
test_data = {
    "enableReasoning": True,
    "maxTokens": 4096,
    "modelId": "gpt-4o",
    "reasoningEffort": "high",
    "temperature": 0.7
}

print("Testing ConfigUpdate with frontend data:")
print(json.dumps(test_data, indent=2))

try:
    update = ConfigUpdate(**test_data)
    print("\n✓ ConfigUpdate created successfully!")
    print(f"Parsed fields: {update.dict(exclude_unset=True)}")
except Exception as e:
    print(f"\n✗ Error creating ConfigUpdate: {e}")
    if hasattr(e, 'errors'):
        for error in e.errors():
            print(f"  - {error}")
