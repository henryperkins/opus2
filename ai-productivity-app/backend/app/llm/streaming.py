import asyncio
import json
from datetime import datetime
from typing import AsyncIterator, Optional

from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class StreamingHandler:
    """Handle streaming LLM responses over WebSocket."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.message_id = None
        self.buffer = []
        self.total_tokens = 0

    async def stream_response(
        self,
        response_generator: AsyncIterator[str],
        message_id: int
    ):
        """Stream LLM response chunks to WebSocket."""
        self.message_id = message_id

        try:
            async for chunk in response_generator:
                self.buffer.append(chunk)
                self.total_tokens += len(chunk) // 4  # Rough estimate

                # Send chunk
                chunk_data = {
                    'type': 'ai_stream',
                    'message_id': message_id,
                    'content': chunk,
                    'done': False
                }
                await self.websocket.send_json(chunk_data)

                # Small delay to prevent overwhelming client
                await asyncio.sleep(0.01)

            # Send completion
            full_content = ''.join(self.buffer)
            
            # Ensure we don't return empty content (violates database constraint)
            if not full_content.strip():
                full_content = "I apologize, but I wasn't able to generate a response. Please try again."
            
            await self.websocket.send_json({
                'type': 'ai_stream',
                'message_id': message_id,
                'content': '',
                'done': True,
                'message': {
                    'id': message_id,
                    'content': full_content,
                    'role': 'assistant',
                    'created_at': datetime.now().isoformat()
                }
            })

            return full_content

        except Exception as e:
            logger.error(f"Streaming error: {e}")

            # Send error message
            await self.websocket.send_json({
                'type': 'ai_stream',
                'message_id': message_id,
                'error': str(e),
                'done': True
            })

            raise

    async def handle_code_generation(
        self,
        content: str,
        language: str,
        websocket: WebSocket
    ):
        """Special handling for code generation responses."""
        # Track code blocks
        code_blocks = []
        current_block = []
        in_code_block = False
        current_language = None

        lines = content.split('\n')

        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # End of code block
                    code_blocks.append({
                        'language': current_language or language,
                        'code': '\n'.join(current_block)
                    })
                    current_block = []
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True
                    current_language = line[3:].strip() or language
            elif in_code_block:
                current_block.append(line)

        # Send code blocks separately for highlighting
        for i, block in enumerate(code_blocks):
            await websocket.send_json({
                'type': 'code_block',
                'index': i,
                'language': block['language'],
                'code': block['code']
            })
