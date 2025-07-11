"""Mock WebSocket for REST API integration."""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MockWebSocket:
    """Mock WebSocket for use in REST API when no real WebSocket is available."""

    def __init__(self):
        self.messages = []

    async def send_json(self, data: Dict[str, Any]):
        """Mock send_json that logs the message instead of sending it."""
        logger.debug(f"Mock WebSocket would send: {data}")
        self.messages.append(data)

    async def send_text(self, text: str):
        """Mock send_text that logs the message instead of sending it."""
        logger.debug(f"Mock WebSocket would send text: {text}")
        self.messages.append({"type": "text", "content": text})

    def get_messages(self):
        """Get all messages that would have been sent."""
        return self.messages

    def clear_messages(self):
        """Clear message history."""
        self.messages.clear()
