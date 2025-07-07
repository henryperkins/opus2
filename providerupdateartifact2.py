# Complete implementation for partial function call streaming
# This reduces API calls from 3 to 1-2 per user message

# ========== app/llm/streaming.py - Enhanced streaming handler ==========

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

    # ... existing methods remain the same ...


class EnhancedStreamingHandler(StreamingHandler):
    """Enhanced handler with partial function call streaming support."""

    def __init__(self, websocket: WebSocket):
        super().__init__(websocket)
        self.tool_calls = []
        self.current_tool_calls = {}  # Track in-progress tool calls by index

    async def stream_response_with_tools(
        self,
        response_generator: AsyncIterator[Any],
        message_id: int
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
            full_content = ''.join(self.buffer) or "I'll help you with that."

            # Only send completion if we had content (not just tool calls)
            if content_started or not self.tool_calls:
                await self.websocket.send_json({
                    'type': 'ai_stream',
                    'message_id': message_id,
                    'content': '',
                    'done': True,
                    'has_tool_calls': len(self.tool_calls) > 0,
                    'message': {
                        'id': message_id,
                        'content': full_content,
                        'role': 'assistant',
                        'created_at': datetime.now().isoformat()
                    }
                })

            return full_content, self.tool_calls

        except Exception as e:
            logger.error(f"Enhanced streaming error: {e}", exc_info=True)
            await self.websocket.send_json({
                'type': 'ai_stream',
                'message_id': message_id,
                'error': str(e),
                'done': True
            })
            raise

    async def _handle_openai_chunk(self, chunk: Any, message_id: int, content_started: bool):
        """Handle OpenAI/Azure Chat Completions streaming chunk."""
        choice = chunk.choices[0]

        # Handle finish reason
        if choice.finish_reason == "tool_calls":
            # Notify client that tool calls are being processed
            if not content_started:
                await self.websocket.send_json({
                    'type': 'ai_tool_start',
                    'message_id': message_id,
                    'content': 'Processing your request...'
                })

        # Handle tool calls in the delta
        if hasattr(choice.delta, "tool_calls") and choice.delta.tool_calls:
            for tool_call_delta in choice.delta.tool_calls:
                await self._process_tool_call_delta(tool_call_delta)

        # Handle regular content
        elif hasattr(choice.delta, "content") and choice.delta.content:
            self.buffer.append(choice.delta.content)
            self.total_tokens += len(choice.delta.content) // 4

            # Stream content to client
            await self.websocket.send_json({
                'type': 'ai_stream',
                'message_id': message_id,
                'content': choice.delta.content,
                'done': False
            })

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
                "arguments": ""
            }

            # Notify client
            await self.websocket.send_json({
                'type': 'ai_tool_call',
                'message_id': message_id,
                'tool_name': name,
                'status': 'started'
            })

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
            await self.websocket.send_json({
                'type': 'ai_stream',
                'message_id': message_id,
                'content': chunk.delta,
                'done': False
            })

    async def _process_tool_call_delta(self, tool_call_delta: Any):
        """Process incremental tool call update."""
        index = getattr(tool_call_delta, "index", 0)

        # Initialize tool call if needed
        if index not in self.current_tool_calls:
            self.current_tool_calls[index] = {
                "id": getattr(tool_call_delta, "id", f"call_{index}"),
                "type": getattr(tool_call_delta, "type", "function"),
                "function": {
                    "name": "",
                    "arguments": ""
                }
            }

        current_call = self.current_tool_calls[index]

        # Update function name if provided
        if hasattr(tool_call_delta, "function"):
            if hasattr(tool_call_delta.function, "name") and tool_call_delta.function.name:
                current_call["function"]["name"] = tool_call_delta.function.name

                # Notify client when we know the function name
                await self.websocket.send_json({
                    'type': 'ai_tool_call',
                    'message_id': self.message_id,
                    'tool_name': tool_call_delta.function.name,
                    'status': 'started'
                })

            # Accumulate arguments
            if hasattr(tool_call_delta.function, "arguments"):
                current_call["function"]["arguments"] += tool_call_delta.function.arguments

    def _finalize_tool_calls(self):
        """Convert in-progress tool calls to final format."""
        for index in sorted(self.current_tool_calls.keys()):
            call = self.current_tool_calls[index]

            # Convert to simple format for processor
            self.tool_calls.append({
                "id": call["id"],
                "name": call["function"]["name"],
                "arguments": call["function"]["arguments"]
            })


# ========== app/chat/processor.py - Modified chat processor ==========

# Replace the _respond_with_llm method with this enhanced version:

async def _respond_with_llm(
    self,
    *,
    session_id: int,
    prompt: str,
    context: Dict[str, Any],
    websocket: WebSocket,
) -> str:
    """End-to-end LLM orchestration with single-pass streaming and tool calls."""

    # Create placeholder message
    ai_msg = await self.chat_service.create_message(
        session_id=session_id,
        content="Generating response…",
        role="assistant",
        rag_metadata=context.get("rag_metadata", {}),
        broadcast=False,
    )

    # Build prompt messages
    messages, _ = await self._assemble_llm_messages(
        session_id=session_id,
        prompt=prompt,
        context=context,
    )

    # Get runtime configuration
    cfg = llm_client._get_runtime_config()
    active_model = cfg.get("chat_model", llm_client.active_model)
    is_reasoning_model = (
        llm_client._is_reasoning_model(active_model)
        if hasattr(llm_client, "_is_reasoning_model")
        else False
    )

    # Get tools to use
    tools_to_use = (
        llm_tools.TOOL_SCHEMAS[: settings.max_tools_per_request]
        if hasattr(settings, "max_tools_per_request")
        else llm_tools.TOOL_SCHEMAS
    )

    # NEW: Single streaming call with tools enabled
    logger.info("Starting streaming completion with tools enabled")
    stream = await llm_client.complete(
        messages=messages,
        temperature=cfg.get("temperature"),
        stream=True,  # Enable streaming from the start
        tools=tools_to_use,  # Include tools in streaming call
        tool_choice="auto",
        parallel_tool_calls=True,
        reasoning=(
            settings.enable_reasoning if not is_reasoning_model else None
        ),
        max_tokens=cfg.get("max_tokens"),
    )

    # Use enhanced handler for streaming with tool support
    handler = EnhancedStreamingHandler(websocket)
    full_response, tool_calls = await handler.stream_response_with_tools(stream, ai_msg.id)

    # Process any tool calls that came through
    rounds = 0
    while tool_calls and rounds < MAX_TOOL_CALL_ROUNDS:
        rounds += 1
        logger.info(f"Processing {len(tool_calls)} tool calls (round {rounds})")

        # Notify client about tool execution
        await websocket.send_json({
            'type': 'ai_tools_executing',
            'message_id': ai_msg.id,
            'tool_count': len(tool_calls),
            'tools': [{"name": tc["name"]} for tc in tool_calls]
        })

        # Execute tools in parallel
        tool_results = await self._run_parallel_tool_calls(tool_calls)
        messages.extend(tool_results["message_deltas"])

        # Stream the response after tool execution
        logger.info("Streaming response after tool execution")
        stream = await llm_client.complete(
            messages=messages,
            temperature=cfg.get("temperature"),
            stream=True,
            tools=tools_to_use if rounds < MAX_TOOL_CALL_ROUNDS - 1 else None,
            tool_choice="auto" if rounds < MAX_TOOL_CALL_ROUNDS - 1 else None,
            max_tokens=cfg.get("max_tokens"),
        )

        # Continue streaming
        handler = EnhancedStreamingHandler(websocket)
        tool_response, tool_calls = await handler.stream_response_with_tools(stream, ai_msg.id)
        full_response += "\n\n" + tool_response if full_response else tool_response

    if rounds >= MAX_TOOL_CALL_ROUNDS:
        logger.warning(f"Reached max tool rounds ({MAX_TOOL_CALL_ROUNDS})")

    # Add confidence warnings if needed
    enhanced_response = await self._add_confidence_warnings(full_response, context)

    # Update message
    await self.chat_service.update_message_content(
        message_id=ai_msg.id,
        content=enhanced_response,
        code_snippets=self._extract_code_snippets(enhanced_response),
        broadcast=True,
    )

    # Track analytics
    asyncio.create_task(
        self._track_response_quality(
            ai_msg.id, ai_msg.session_id, context, full_response
        )
    )

    return enhanced_response


# Add new parallel tool execution method:
async def _run_parallel_tool_calls(
    self,
    tool_calls: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Execute multiple tool calls in parallel."""

    async def execute_single_tool(call: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Execute a single tool and return (call, result)."""
        name = call["name"]
        try:
            args = json.loads(call["arguments"])
        except Exception as exc:
            logger.error(f"Tool call argument decode failed: {exc}")
            args = {}

        logger.info(f"Executing tool {name}")
        try:
            result = await asyncio.wait_for(
                llm_tools.call_tool(name, args, self.db),
                timeout=getattr(settings, "tool_timeout", 30),
            )
            return call, result
        except asyncio.TimeoutError:
            logger.error(f"Tool '{name}' timed out")
            return call, {
                "success": False,
                "error": f"Tool execution timed out after {getattr(settings, 'tool_timeout', 30)} seconds",
                "error_type": "timeout",
            }
        except Exception as exc:
            logger.error(f"Tool '{name}' failed: {exc}", exc_info=True)
            return call, {
                "success": False,
                "error": str(exc),
                "error_type": "execution_exception",
            }

    # Execute all tools in parallel
    results = await asyncio.gather(
        *[execute_single_tool(call) for call in tool_calls],
        return_exceptions=False
    )

    # Format results for message deltas
    deltas = []
    for call, result in results:
        formatted_output = llm_tools.format_tool_result_for_api(result)

        if getattr(llm_client, "use_responses_api", False):
            deltas.append({
                "type": "function_call_output",
                "call_id": call.get("id", "unknown"),
                "output": formatted_output,
            })
        else:
            deltas.append({
                "role": "tool",
                "tool_call_id": call.get("id", "unknown"),
                "name": call["name"],
                "content": formatted_output,
            })

    return {"message_deltas": deltas}


# ========== app/config.py - Add new settings ==========

class Settings(BaseSettings):
    # ... existing settings ...

    # Tool execution settings
    max_tools_per_request: int = Field(
        default=10,
        description="Maximum number of tools to send per request"
    )
    tool_timeout: int = Field(
        default=30,
        description="Timeout for individual tool execution in seconds"
    )

    # Streaming settings
    stream_chunk_delay_ms: int = Field(
        default=1,
        description="Delay between streaming chunks in milliseconds"
    )
