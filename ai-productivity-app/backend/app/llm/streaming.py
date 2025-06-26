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

        # Defensive guard: if the caller forgot stream=True, fall back to non-streaming
        if not hasattr(response_generator, "__aiter__"):
            # Extract response content from non-streaming response using same logic as processor
            full_text = ""
            
            # Azure Responses API format
            if hasattr(response_generator, 'output') and response_generator.output:
                for item in response_generator.output:
                    if (getattr(item, "type", None) == "message" and
                            hasattr(item, "content") and item.content):
                        if isinstance(item.content, str):
                            full_text = item.content
                            break
                        # Handle structured content (e.g., with reasoning)
                        elif isinstance(item.content, list) and item.content:
                            text_parts = []
                            for content_item in item.content:
                                if hasattr(content_item, "text"):
                                    text_parts.append(content_item.text)
                            full_text = "\n".join(text_parts) if text_parts else str(item.content[0])
                            break
                        else:
                            full_text = str(item.content)
                            break
            # Legacy formats
            elif hasattr(response_generator, 'output_text'):
                full_text = response_generator.output_text or ""
            elif hasattr(response_generator, 'choices') and response_generator.choices:
                full_text = response_generator.choices[0].message.content or ""
            else:
                full_text = str(response_generator)
            
            # Ensure we don't return empty content
            if not full_text.strip():
                full_text = "I apologize, but I wasn't able to generate a response. Please try again."
            
            # Send as single complete message
            await self.websocket.send_json({
                'type': 'ai_stream',
                'message_id': message_id,
                'content': full_text,
                'done': True,
                'message': {
                    'id': message_id,
                    'content': full_text,
                    'role': 'assistant',
                    'created_at': datetime.now().isoformat()
                }
            })
            return full_text

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
