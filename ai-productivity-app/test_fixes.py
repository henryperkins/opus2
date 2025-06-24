#!/usr/bin/env python3
"""
Test script to validate the fixes without running the full auto_align_db.py
"""

def test_chat_session_fix():
    """Test that ChatSession.is_active issue has been addressed"""
    print("🧪 Testing ChatSession.is_active fix...")

    # Read the chat_service.py file to verify the fix
    with open('/home/azureuser/opus2/ai-productivity-app/backend/app/services/chat_service.py', 'r') as f:
        content = f.read()

    # Check for explicit is_active=True setting
    if 'is_active=True' in content:
        print("✅ Found explicit is_active=True in ChatSession creation")
    else:
        print("❌ Missing explicit is_active=True")

    # Check for db.refresh call
    if 'db.refresh(session)' in content:
        print("✅ Found db.refresh(session) call")
    else:
        print("❌ Missing db.refresh(session) call")

def test_knowledge_route_fix():
    """Test that knowledge search route compatibility has been added"""
    print("\n🧪 Testing knowledge search route fix...")

    # Read the knowledge.py file to verify the fix
    with open('/home/azureuser/opus2/ai-productivity-app/backend/app/routers/knowledge.py', 'r') as f:
        content = f.read()

    # Check for backward compatibility route
    if '/search/{project_id}' in content:
        print("✅ Found backward-compatible route /search/{project_id}")
    else:
        print("❌ Missing backward-compatible route")

    # Check for proper forwarding
    if 'search_knowledge_by_project' in content:
        print("✅ Found search_knowledge_by_project function")
    else:
        print("❌ Missing search_knowledge_by_project function")

def test_auto_align_enhancements():
    """Test that auto_align_db.py has been enhanced"""
    print("\n🧪 Testing auto_align_db.py enhancements...")

    # Read the auto_align_db.py file to verify enhancements
    with open('/home/azureuser/opus2/ai-productivity-app/backend/scripts/auto_align_db.py', 'r') as f:
        content = f.read()

    # Check for server_default detection
    if 'detect_server_default_mismatches' in content:
        print("✅ Found detect_server_default_mismatches method")
    else:
        print("❌ Missing detect_server_default_mismatches method")

    # Check for suggestion display
    if 'suggestion' in content and '💡 Suggestion:' in content:
        print("✅ Found suggestion display enhancement")
    else:
        print("❌ Missing suggestion display")

def main():
    """Run all tests"""
    print("🔧 Running validation tests for the fixes...\n")

    test_chat_session_fix()
    test_knowledge_route_fix()
    test_auto_align_enhancements()

    print("\n✨ Validation complete!")

if __name__ == "__main__":
    main()
