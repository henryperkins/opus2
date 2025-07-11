import asyncio
import json
from datetime import datetime
from typing import AsyncIterator, Optional, List, Dict, Any, Tuple

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
        self, response_generator: AsyncIterator[str], message_id: int
    ):
        """Stream LLM response chunks to WebSocket."""
        self.message_id = message_id

        # Defensive guard: if the caller forgot stream=True, fall back to non-streaming
        if not hasattr(response_generator, "__aiter__"):
            # Extract response content from non-streaming response using same logic as processor
            full_text = ""

            # Azure Responses API format
            if hasattr(response_generator, "output") and response_generator.output:
                for item in response_generator.output:
                    if (
                        getattr(item, "type", None) == "message"
                        and hasattr(item, "content")
                        and item.content
                    ):
                        if isinstance(item.content, str):
                            full_text = item.content
                            break
                        # Handle structured content (e.g., with reasoning)
                        elif isinstance(item.content, list) and item.content:
                            text_parts = []
                            for content_item in item.content:
                                if hasattr(content_item, "text"):
                                    text_parts.append(content_item.text)
                            full_text = (
                                "\n".join(text_parts)
                                if text_parts
                                else str(item.content[0])
                            )
                            break
                        else:
                            full_text = str(item.content)
                            break
            # Legacy formats
            elif hasattr(response_generator, "output_text"):
                full_text = response_generator.output_text or ""
            elif hasattr(response_generator, "choices") and response_generator.choices:
                full_text = response_generator.choices[0].message.content or ""
            else:
                full_text = str(response_generator)

            # Ensure we don't return empty content
            if not full_text.strip():
                full_text = "I apologize, but I wasn't able to generate a response. Please try again."

            # Send as single complete message
            await self.websocket.send_json(
                {
                    "type": "ai_stream",
                    "message_id": message_id,
                    "content": full_text,
                    "done": True,
                    "message": {
                        "id": message_id,
                        "content": full_text,
                        "role": "assistant",
                        "created_at": datetime.now().isoformat(),
                    },
                }
            )
            return full_text

        try:
            async for chunk in response_generator:
                self.buffer.append(chunk)
                self.total_tokens += len(chunk) // 4  # Rough estimate

                # Send chunk
                chunk_data = {
                    "type": "ai_stream",
                    "message_id": message_id,
                    "content": chunk,
                    "done": False,
                }
                await self.websocket.send_json(chunk_data)

                # Small delay to prevent overwhelming client
                await asyncio.sleep(0.01)

            # Send completion
            full_content = "".join(self.buffer)

            # Ensure we don't return empty content (violates database constraint)
            if not full_content.strip():
                full_content = "I apologize, but I wasn't able to generate a response. Please try again."

            await self.websocket.send_json(
                {
                    "type": "ai_stream",
                    "message_id": message_id,
                    "content": "",
                    "done": True,
                    "message": {
                        "id": message_id,
                        "content": full_content,
                        "role": "assistant",
                        "created_at": datetime.now().isoformat(),
                    },
                }
            )

            return full_content

        except Exception as e:
            logger.error(f"Streaming error: {e}")

            # Send error message
            await self.websocket.send_json(
                {
                    "type": "ai_stream",
                    "message_id": message_id,
                    "error": str(e),
                    "done": True,
                }
            )

            raise

    async def handle_code_generation(
        self, content: str, language: str, websocket: WebSocket
    ):
        """Special handling for code generation responses."""
        # Track code blocks
        code_blocks = []
        current_block = []
        in_code_block = False
        current_language = None

        lines = content.split("\n")

        for line in lines:
            if line.startswith("```"):
                if in_code_block:
                    # End of code block
                    code_blocks.append(
                        {
                            "language": current_language or language,
                            "code": "\n".join(current_block),
                        }
                    )
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
            await websocket.send_json(
                {
                    "type": "code_block",
                    "index": i,
                    "language": block["language"],
                    "code": block["code"],
                }
            )


class EnhancedStreamingHandler(StreamingHandler):
    """Enhanced handler with partial function call streaming support."""

    def __init__(self, websocket: WebSocket):
        super().__init__(websocket)
        self.tool_calls = []
        self.current_tool_calls = {}  # Track in-progress tool calls by index

    async def stream_response_with_tools(
        self, response_generator: AsyncIterator[Any], message_id: int
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Stream response and collect tool calls.

        Returns:
            Tuple of (full_response_text, tool_calls)
        """
        self.message_id = message_id
        self.tool_calls = []
        self.current_tool_calls = {}
        content_started = False

        try:
            async for chunk in response_generator:
                # Handle different response formats
                if hasattr(chunk, "choices") and chunk.choices:
                    await self._handle_openai_chunk(chunk, message_id, content_started)
                    if chunk.choices[0].delta.content:
                        content_started = True

                elif hasattr(chunk, "type"):
                    # Azure Responses API format
                    await self._handle_azure_chunk(chunk, message_id)

                # Small delay to prevent overwhelming client
                await asyncio.sleep(0.001)

            # Finalize any pending tool calls
            self._finalize_tool_calls()

            # Send completion
            full_content = "".join(self.buffer) or "I'll help you with that."

            # Only send completion if we had content (not just tool calls)
            if content_started or not self.tool_calls:
                await self.websocket.send_json(
                    {
                        "type": "ai_stream",
                        "message_id": message_id,
                        "content": "",
                        "done": True,
                        "has_tool_calls": len(self.tool_calls) > 0,
                        "message": {
                            "id": message_id,
                            "content": full_content,
                            "role": "assistant",
                            "created_at": datetime.now().isoformat(),
                        },
                    }
                )

            return full_content, self.tool_calls

        except Exception as e:
            logger.error(f"Enhanced streaming error: {e}", exc_info=True)
            await self.websocket.send_json(
                {
                    "type": "ai_stream",
                    "message_id": message_id,
                    "error": str(e),
                    "done": True,
                }
            )
            raise

    async def _handle_openai_chunk(
        self, chunk: Any, message_id: int, content_started: bool
    ):
        """Handle OpenAI/Azure Chat Completions streaming chunk."""
        choice = chunk.choices[0]

        # Handle finish reason
        if choice.finish_reason == "tool_calls":
            # Notify client that tool calls are being processed
            if not content_started:
                await self.websocket.send_json(
                    {
                        "type": "ai_tool_start",
                        "message_id": message_id,
                        "content": "Processing your request...",
                    }
                )

        # Handle tool calls in the delta
        if hasattr(choice.delta, "tool_calls") and choice.delta.tool_calls:
            for tool_call_delta in choice.delta.tool_calls:
                await self._process_tool_call_delta(tool_call_delta)

        # Handle regular content
        elif hasattr(choice.delta, "content") and choice.delta.content:
            self.buffer.append(choice.delta.content)
            self.total_tokens += len(choice.delta.content) // 4

            # Stream content to client
            await self.websocket.send_json(
                {
                    "type": "ai_stream",
                    "message_id": message_id,
                    "content": choice.delta.content,
                    "done": False,
                }
            )

    async def _handle_azure_chunk(self, chunk: Any, message_id: int):
        """Handle Azure Responses API streaming chunk."""
        event_type = getattr(chunk, "type", None)

        if event_type == "response.function_call.start":
            # New function call starting
            call_id = getattr(chunk, "call_id", f"call_{len(self.tool_calls)}")
            name = getattr(chunk, "name", "unknown")

            self.current_tool_calls[call_id] = {
                "id": call_id,
                "name": name,
                "arguments": "",
            }

            # Notify client
            await self.websocket.send_json(
                {
                    "type": "ai_tool_call",
                    "message_id": message_id,
                    "tool_name": name,
                    "status": "started",
                }
            )

        elif event_type == "response.function_call.arguments.delta":
            # Function arguments streaming
            call_id = getattr(chunk, "call_id", None)
            delta = getattr(chunk, "delta", "")

            if call_id and call_id in self.current_tool_calls:
                self.current_tool_calls[call_id]["arguments"] += delta

        elif event_type == "response.function_call.done":
            # Function call complete
            call_id = getattr(chunk, "call_id", None)
            if call_id and call_id in self.current_tool_calls:
                self.tool_calls.append(self.current_tool_calls[call_id])
                del self.current_tool_calls[call_id]

        # Handle text content
        elif hasattr(chunk, "delta") and chunk.delta:
            self.buffer.append(chunk.delta)
            await self.websocket.send_json(
                {
                    "type": "ai_stream",
                    "message_id": message_id,
                    "content": chunk.delta,
                    "done": False,
                }
            )

    async def _process_tool_call_delta(self, tool_call_delta: Any):
        """Process incremental tool call update."""
        index = getattr(tool_call_delta, "index", 0)

        # Initialize tool call if needed
        if index not in self.current_tool_calls:
            self.current_tool_calls[index] = {
                "id": getattr(tool_call_delta, "id", f"call_{index}"),
                "type": getattr(tool_call_delta, "type", "function"),
                "function": {"name": "", "arguments": ""},
            }

        current_call = self.current_tool_calls[index]

        # Update function name if provided
        if hasattr(tool_call_delta, "function"):
            if (
                hasattr(tool_call_delta.function, "name")
                and tool_call_delta.function.name
            ):
                current_call["function"]["name"] = tool_call_delta.function.name

                # Notify client when we know the function name
                await self.websocket.send_json(
                    {
                        "type": "ai_tool_call",
                        "message_id": self.message_id,
                        "tool_name": tool_call_delta.function.name,
                        "status": "started",
                    }
                )

            # Accumulate arguments
            if hasattr(tool_call_delta.function, "arguments"):
                current_call["function"][
                    "arguments"
                ] += tool_call_delta.function.arguments

    def _finalize_tool_calls(self):
        """Convert in-progress tool calls to final format."""
        for index in sorted(self.current_tool_calls.keys()):
            call = self.current_tool_calls[index]

            # Convert to simple format for processor
            self.tool_calls.append(
                {
                    "id": call["id"],
                    "name": call["function"]["name"],
                    "arguments": call["function"]["arguments"],
                }
            )
