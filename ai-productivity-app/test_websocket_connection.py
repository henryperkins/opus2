#!/usr/bin/env python3
"""
Test script to verify WebSocket conversation history functionality.

This script follows the run-book steps to:
1. Authenticate and get a JWT token
2. Create or get a chat session
3. Test WebSocket connection
4. Verify database persistence
"""

import asyncio
import json
import requests
import websockets
import psycopg2
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_5odQclNUW6Pj@ep-hidden-salad-a8jlsv5j-pooler.eastus2.azure.neon.tech/neondb?sslmode=require&channel_binding=require")


def get_auth_token():
    """Authenticate and get JWT token from cookie."""
    print("🔐 Authenticating...")

    # Register a test user or login with existing credentials
    auth_data = {
        "username": "testuser_ws",
        "email": "testuser_ws@example.com",
        "password": "testpassword123"
    }

    session = requests.Session()

    # Try to register (may fail if user exists)
    try:
        response = session.post(f"{BASE_URL}/api/auth/register", json=auth_data)
        if response.status_code == 201:
            print("✅ User registered successfully")
        else:
            print(f"ℹ️ Registration failed (user may exist): {response.status_code}")
    except Exception as e:
        print(f"ℹ️ Registration error (user may exist): {e}")

    # Login to get token
    login_data = {
        "username_or_email": auth_data["username"],
        "password": auth_data["password"]
    }

    response = session.post(f"{BASE_URL}/api/auth/login", json=login_data)
    if response.status_code == 200:
        print("✅ Login successful")
        # Extract token from cookie
        access_token = None
        for cookie in session.cookies:
            if cookie.name == "access_token":
                access_token = cookie.value
                break

        if access_token:
            print(f"✅ Got JWT token: {access_token[:20]}...")
            return access_token, session
        else:
            raise Exception("No access_token cookie found")
    else:
        raise Exception(f"Login failed: {response.status_code} - {response.text}")


def create_test_session(session, project_id=1):
    """Create a test chat session."""
    print("📝 Creating test chat session...")

    session_data = {
        "project_id": project_id,
        "title": f"Test Session - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    }

    response = session.post(f"{BASE_URL}/api/chat/sessions", json=session_data)
    if response.status_code == 201:
        session_info = response.json()
        print(f"✅ Chat session created: ID {session_info['id']}")
        return session_info['id']
    else:
        raise Exception(f"Failed to create session: {response.status_code} - {response.text}")


async def test_websocket_connection(session_id, token):
    """Test WebSocket connection and message flow."""
    print(f"🔌 Testing WebSocket connection to session {session_id}...")

    # Build WebSocket URL with token
    ws_url = f"ws://localhost:8000/api/chat/ws/sessions/{session_id}?token={token}"

    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected")

            # Wait for initial frames
            messages_received = []

            # Listen for initial messages (should get 'connected' and 'message_history')
            try:
                for i in range(2):  # Expect at least 2 initial frames
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    messages_received.append(data)
                    print(f"📨 Received: {data['type']}")

                    if data['type'] == 'message_history':
                        print(f"📜 Message history: {len(data.get('messages', []))} messages")
            except asyncio.TimeoutError:
                print("⚠️ Timeout waiting for initial messages")

            # Send a test message
            test_message = {
                "type": "message",
                "content": "Hello, this is a test message for WebSocket verification!",
                "metadata": {}
            }

            print("📤 Sending test message...")
            await websocket.send(json.dumps(test_message))

            # Wait for response frames
            try:
                for i in range(3):  # Expect echo + AI response
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    messages_received.append(data)
                    print(f"📨 Received: {data['type']} - {data.get('content', '')[:50]}...")
            except asyncio.TimeoutError:
                print("⚠️ Timeout waiting for response messages")

            return messages_received

    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return []


def verify_database_persistence(session_id):
    """Verify messages are persisted in PostgreSQL."""
    print("🗄️ Verifying database persistence...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Query recent messages for the session
        query = """
        SELECT id, role, LEFT(content, 60) AS snippet,
               created_at::text, is_deleted
        FROM chat_messages
        WHERE session_id = %s
        ORDER BY created_at DESC
        LIMIT 20;
        """

        cursor.execute(query, (session_id,))
        rows = cursor.fetchall()

        print(f"📊 Database contains {len(rows)} messages for session {session_id}")

        for row in rows:
            msg_id, role, snippet, created_at, is_deleted = row
            print(f"  ID:{msg_id} | {role} | {snippet}... | {created_at} | deleted:{is_deleted}")

        # Check timestamp integrity
        if len(rows) > 1:
            cursor.execute("""
            SELECT MAX(created_at) - MIN(created_at) as timespan
            FROM chat_messages
            WHERE session_id = %s;
            """, (session_id,))

            timespan = cursor.fetchone()[0]
            print(f"⏱️ Conversation timespan: {timespan}")

        cursor.close()
        conn.close()

        return len(rows)

    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return 0


def check_backend_logs():
    """Check backend logs for WebSocket connection info."""
    print("📋 Checking backend logs...")

    try:
        result = os.popen("cd /home/azureuser/opus2/ai-productivity-app && docker compose logs --tail=20 backend | grep -E 'WebSocket|Accepted|Disconnected'").read()
        if result.strip():
            print("📄 Recent WebSocket activity:")
            for line in result.strip().split('\n'):
                print(f"  {line}")
        else:
            print("ℹ️ No recent WebSocket activity in logs")
    except Exception as e:
        print(f"⚠️ Could not check logs: {e}")


async def main():
    """Main test function following the run-book."""
    print("🚀 Starting WebSocket conversation history verification\n")

    try:
        # Step 1: Get authentication
        token, http_session = get_auth_token()

        # Step 2: Create test session
        session_id = create_test_session(http_session)

        # Step 3: Test WebSocket connection
        ws_messages = await test_websocket_connection(session_id, token)

        # Step 4: Verify database persistence
        db_message_count = verify_database_persistence(session_id)

        # Step 5: Check logs
        check_backend_logs()

        # Summary
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"✅ Authentication: {'PASS' if token else 'FAIL'}")
        print(f"✅ Session Creation: {'PASS' if session_id else 'FAIL'}")
        print(f"✅ WebSocket Messages: {len(ws_messages)} received")
        print(f"✅ Database Persistence: {db_message_count} messages stored")

        # Check for expected message types
        msg_types = [msg.get('type') for msg in ws_messages]
        expected_types = ['connected', 'message_history']

        for expected in expected_types:
            if expected in msg_types:
                print(f"✅ Received expected '{expected}' message")
            else:
                print(f"❌ Missing expected '{expected}' message")

        if len(ws_messages) >= 2 and db_message_count > 0:
            print("\n🎉 SUCCESS: WebSocket conversation history is working correctly!")
            return True
        else:
            print("\n❌ FAILURE: Some aspects of the conversation history are not working")
            return False

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
