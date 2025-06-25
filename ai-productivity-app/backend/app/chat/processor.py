from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from fastapi import WebSocket
import logging
import asyncio
import json

from app.models.chat import ChatSession, ChatMessage
from app.models.project import Project
from app.services.chat_service import ChatService
from app.llm.client import llm_client
from app.llm.streaming import StreamingHandler
from app.llm import tools as llm_tools
# Local
from app.config import settings  # Required for ``settings.enable_reasoning`` in _generate_ai_response
from .context_builder import ContextBuilder
from .commands import command_registry
from .secret_scanner import secret_scanner

logger = logging.getLogger(__name__)


class ChatProcessor:
    """Process chat messages with AI assistance."""

    def __init__(self, db: Session):
        self.db = db
        self.chat_service = ChatService(db)
        self.context_builder = ContextBuilder(db)

    async def process_message(
        self,
        session_id: int,
        message: ChatMessage,
        websocket: WebSocket
    ):
        """Process user message and generate AI response."""
        try:
            # Get session and project
            session = self.db.query(ChatSession).filter_by(id=session_id).first()
            if not session:
                raise ValueError("Session not found")

            # Secret scanning
            validation = secret_scanner.validate_message(message.content)
            if not validation['valid']:
                # Redact and warn
                redacted = secret_scanner.redact(message.content, validation['findings'])

                # Update message with redacted content
                message.content = redacted
                self.db.commit()

                # Send warning
                await websocket.send_json({
                    'type': 'warning',
                    'message': f"Secrets detected and redacted: {validation['message']}"
                })

            # Extract context
            context = self.context_builder.extract_context(
                message.content,
                session.project_id
            )
            context['project_id'] = session.project_id

            # Store context references in message
            message.referenced_files = [ref['path'] for ref in context['file_references']]
            message.referenced_chunks = [c['document_id'] for c in context['chunks']]
            self.db.commit()

            # ------------------------------------------------------------------ #
            # Inform all connected clients that the previously *placeholder*
            # assistant message has been replaced by the final model output.
            # ------------------------------------------------------------------ #

            try:
                from app.websocket.manager import connection_manager

                await connection_manager.send_message(
                    {
                        "type": "message_update",
                        "message_id": ai_message.id,
                        "updates": {
                            "content": full_response,
                            "edited": False,
                        },
                    },
                    session_id,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("WebSocket update broadcast failed: %s", exc)

            # Create timeline event for analytics (integrates with existing timeline system)
            self.context_builder.create_timeline_event(
                session_id=session_id,
                message_content=message.content,
                referenced_files=message.referenced_files
            )

            # Execute slash commands
            commands = await command_registry.execute_commands(
                message.content,
                context,
                self.db
            )

            if commands:
                message.applied_commands = {
                    cmd['command']: cmd.get('prompt', cmd.get('message', ''))
                    for cmd in commands
                }
                self.db.commit()

                # Handle command results
                for cmd_result in commands:
                    if cmd_result.get('requires_llm'):
                        # Generate LLM response
                        await self._generate_ai_response(
                            session_id,
                            cmd_result['prompt'],
                            context,
                            websocket
                        )
                    else:
                        # Direct response
                        await self.chat_service.create_message(
                            session_id=session_id,
                            content=cmd_result['message'],
                            role='assistant'
                        )
            else:
                # Regular conversation
                await self._generate_ai_response(
                    session_id,
                    message.content,
                    context,
                    websocket
                )

        except Exception as e:
            logger.error(f"Message processing error: {e}")

            # Send error message
            await self.chat_service.create_message(
                session_id=session_id,
                content=f"I encountered an error processing your message: {str(e)}",
                role='assistant'
            )

    async def _generate_ai_response(
        self,
        session_id: int,
        prompt: str,
        context: Dict,
        websocket: WebSocket
    ):
        """Generate and stream AI response."""
        # ------------------------------------------------------------------ #
        # Runtime configuration                                              #
        # ------------------------------------------------------------------ #

        # Retrieve the *merged* runtime configuration from the global LLM
        # client.  Keys inside the persistent store follow *snake_case*
        # naming (e.g. ``max_tokens``) whereas some callers – in particular
        # the early JavaScript implementation – still use *camelCase*
        # variants.  To guarantee backwards-compatibility we transparently
        # support **both** spellings by first checking the canonical
        # *snake_case* version and falling back to the legacy name.

        runtime_config = llm_client._get_runtime_config()

        def _cfg(key_snake: str, key_camel: str, default: Any | None = None):  # noqa: ANN401
            """Return configuration value supporting *snake* and *camel* keys."""

            return runtime_config.get(key_snake, runtime_config.get(key_camel, default))

        # Maximum number of **context** tokens we are willing to send to the
        # model.  We default to the global *settings* constant when the value
        # is not configured.
        max_context_tokens = _cfg("max_tokens", "maxTokens", settings.max_context_tokens)

        # Reserve tokens for response generation (typically 30-40% of max)
        available_context_tokens = int(max_context_tokens * 0.6)

        # Build conversation history with token management
        conversation = self.context_builder.build_conversation_context(
            session_id=session_id,
            max_tokens=available_context_tokens // 2  # Reserve half for code context
        )

        # Prepare messages for LLM
        system_prompt = """You are an AI coding assistant with access to the project codebase.
You can analyze code, explain functionality, generate tests, and help with development tasks.
Always provide clear, concise, and accurate responses.
When referencing code, mention the file path and line numbers.
Maintain conversation context and refer to previous discussions when relevant."""

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation summary if we have older context
        if conversation and len(conversation) >= 15:  # If we have substantial history
            oldest_message_id = conversation[0]['id']
            summary = self.context_builder.get_conversation_summary(
                session_id=session_id,
                up_to_message_id=oldest_message_id
            )
            if summary:
                messages.append({
                    "role": "system",
                    "content": f"Previous conversation summary: {summary}"
                })

        # Add code context if available
        if context['chunks']:
            code_context = llm_client.prepare_code_context(context['chunks'])
            messages.append({
                "role": "system",
                "content": f"Relevant code context:\n{code_context}"
            })

        # Add conversation history (all messages within token limit)
        for msg in conversation:
            msg_content = msg['content']

            # Enhance message with code context if available
            if msg.get('code_snippets'):
                code_refs = []
                for snippet in msg['code_snippets']:
                    if isinstance(snippet, dict):
                        lang = snippet.get('language', 'text')
                        code_refs.append(f"[{lang} code included]")
                if code_refs:
                    msg_content += f" {' '.join(code_refs)}"

            # Include file references for context continuity
            if msg.get('referenced_files'):
                file_refs = ', '.join(msg['referenced_files'][:3])
                msg_content += f" [Referenced files: {file_refs}]"

            messages.append({
                "role": msg['role'],
                "content": msg_content
            })

        # Add current prompt
        messages.append({
            "role": "user",
            "content": prompt
        })

        # Log context information for debugging
        logger.debug(f"Built LLM context: {len(messages)} messages, {len(conversation)} conversation history, {len(context.get('chunks', []))} code chunks")

        # Log detailed user input and context for debugging
        logger.info("=== USER MESSAGE PROCESSING ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"User Prompt: {prompt}")
        logger.info(f"Context Chunks: {len(context.get('chunks', []))}")
        logger.info(f"File References: {context.get('file_references', [])}")
        logger.info(f"Conversation History: {len(conversation)} messages")
        logger.info(f"Total Messages to LLM: {len(messages)}")

        # Log system prompts and context
        system_messages = [msg for msg in messages if msg['role'] == 'system']
        logger.info(f"System Messages ({len(system_messages)} total):")
        for i, sys_msg in enumerate(system_messages):
            content_preview = sys_msg['content'][:300] + "..." if len(sys_msg['content']) > 300 else sys_msg['content']
            logger.info(f"  System [{i + 1}]: {content_preview}")

        # Log user conversation context
        user_messages = [msg for msg in messages if msg['role'] == 'user']
        logger.info(f"User Messages in Context ({len(user_messages)} total):")
        for i, user_msg in enumerate(user_messages):
            content_preview = user_msg['content'][:200] + "..." if len(user_msg['content']) > 200 else user_msg['content']
            logger.info(f"  User [{i + 1}]: {content_preview}")

        # Create placeholder message
        ai_message = await self.chat_service.create_message(
            session_id=session_id,
            content="Generating response...",
            role='assistant'
        )

        # Stream response
        streaming_handler = StreamingHandler(websocket)

        try:
            # Get runtime configuration for parameters
            runtime_config = llm_client._get_runtime_config()

            # First non-stream call – we need body to inspect potential tool calls
            response = await llm_client.complete(
                messages=messages,
                temperature=_cfg("temperature", "temperature"),  # Always snake
                stream=False,
                tools=llm_tools.TOOL_SCHEMAS,
                reasoning=settings.enable_reasoning,
                max_tokens=_cfg("max_tokens", "maxTokens"),
            )

            # Loop while model wants to call tools - handle both API formats
            tool_call_count = 0
            while self._has_tool_calls(response):
                tool_call_count += 1
                logger.info(f"=== TOOL CALLING ROUND {tool_call_count} ===")

                tool_calls = self._extract_tool_calls(response)
                for tool_call in tool_calls:
                    name = tool_call.get('name')
                    args_json = json.loads(tool_call.get('arguments', '{}'))

                    logger.info(f"Calling tool: {name}")
                    logger.info(f"Tool arguments: {json.dumps(args_json, indent=2)}")

                    result = await llm_tools.call_tool(name, args_json, self.db)

                    logger.info(f"Tool {name} result: {json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)}")

                    # Add tool result to messages - format depends on API type
                    if llm_client.use_responses_api:
                        # Responses API format for tool results
                        messages.append({
                            "type": "function_call_output",
                            "call_id": tool_call.get('id', 'unknown'),
                            "output": json.dumps(result),
                        })
                    else:
                        # Chat Completions API format
                        messages.append({
                            "role": "tool",
                            "name": name,
                            "content": json.dumps(result),
                        })

                # ask LLM to continue with new context
                logger.info("Sending follow-up request to LLM with tool results")
                response = await llm_client.complete(
                    messages=messages,
                    temperature=_cfg("temperature", "temperature"),
                    stream=False,
                    max_tokens=_cfg("max_tokens", "maxTokens"),
                )

            # Extract final assistant content - handle both Chat Completions and Responses API
            final_text = self._extract_response_content(response)

            # Log the AI response for debugging
            logger.info("=== AI RESPONSE RECEIVED ===")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Response Length: {len(final_text)} characters")
            logger.info(f"Response Content: {final_text}")

            # now stream it to client (simulate streaming with proper chunks)
            async def _generator():  # noqa: D401
                # Split response into words for more realistic streaming
                words = final_text.split(' ')
                chunk_size = 3  # Send 3 words per chunk
                
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i + chunk_size])
                    if i + chunk_size < len(words):
                        chunk += ' '  # Add space except for last chunk
                    yield chunk

            full_response = await streaming_handler.stream_response(_generator(), ai_message.id)

            # Update message in DB
            ai_message.content = full_response

            code_snippets = self._extract_code_snippets(full_response)
            if code_snippets:
                ai_message.code_snippets = code_snippets
                logger.info(f"Extracted {len(code_snippets)} code snippets from response")

            self.db.commit()

            # Log final processing results
            logger.info("=== MESSAGE PROCESSING COMPLETE ===")
            logger.info(f"Message ID: {ai_message.id}")
            logger.info(f"Final Response Length: {len(full_response)} characters")
            logger.info(f"Code Snippets: {len(code_snippets) if code_snippets else 0}")

            # Track response quality metrics for analytics
            await self._track_response_quality(ai_message, context, full_response)

        except Exception as e:
            logger.error("AI generation error", exc_info=True)

            # Update placeholder DB record so the user sees a helpful message
            friendly_error = "LLM currently unavailable. Please try again."
            ai_message.content = friendly_error
            self.db.commit()

            # Notify front-end explicitly so it can show a toast / banner
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": friendly_error,
                })
            except Exception:  # pragma: no cover – websocket already gone
                pass

    def _extract_code_snippets(self, text: str) -> List[Dict]:
        """Extract code snippets from response."""
        import re

        snippets = []
        pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)

        for match in pattern.finditer(text):
            language = match.group(1) or 'text'
            code = match.group(2).strip()

            snippets.append({
                'language': language,
                'code': code
            })

        return snippets

    def _extract_response_content(self, response) -> str:
        """Extract text content from either Chat Completions or Responses API response."""
        try:
            # Azure Responses API format
            if hasattr(response, 'output_text') and response.output_text:
                return response.output_text
            elif hasattr(response, 'output') and response.output:
                # Extract text from output array
                if isinstance(response.output, list) and response.output:
                    for output_item in response.output:
                        if hasattr(output_item, 'content') and isinstance(output_item.content, list):
                            for content_item in output_item.content:
                                if hasattr(content_item, 'text'):
                                    return content_item.text
                                elif hasattr(content_item, 'type') and content_item.type == 'output_text':
                                    return getattr(content_item, 'text', str(content_item))
                        elif hasattr(output_item, 'type') and output_item.type == 'message':
                            # Message type output
                            if hasattr(output_item, 'content'):
                                if isinstance(output_item.content, list) and output_item.content:
                                    for content_part in output_item.content:
                                        if hasattr(content_part, 'text'):
                                            return content_part.text
                                elif isinstance(output_item.content, str):
                                    return output_item.content

            # Standard Chat Completions API format
            elif hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    return choice.message.content or ""

            # Fallback for any other response format
            logger.warning(f"Unexpected response format: {type(response)}")
            return str(response)

        except Exception as e:
            logger.error(f"Error extracting response content: {e}", exc_info=True)
            return "Error extracting response content"

    def _has_tool_calls(self, response) -> bool:
        """Check if response contains tool calls (handles both API formats)."""
        try:
            # Chat Completions API format
            if (hasattr(response, "choices")
                and response.choices
                and response.choices[0].finish_reason == "tool_calls"):
                return True

            # Responses API format - check output for function calls
            if hasattr(response, 'output') and response.output:
                if isinstance(response.output, list):
                    for output_item in response.output:
                        if hasattr(output_item, 'type') and output_item.type == 'function_call':
                            return True

            return False
        except Exception:
            return False

    def _extract_tool_calls(self, response) -> List[Dict[str, Any]]:
        """Extract tool calls from response (handles both API formats)."""
        tool_calls = []

        try:
            # Chat Completions API format
            if (hasattr(response, "choices")
                and response.choices
                and hasattr(response.choices[0], 'message')
                and hasattr(response.choices[0].message, 'tool_calls')
                and response.choices[0].message.tool_calls):

                for tool_call in response.choices[0].message.tool_calls:
                    tool_calls.append({
                        'id': getattr(tool_call, 'id', 'unknown'),
                        'name': tool_call.name,
                        'arguments': tool_call.arguments
                    })

            # Responses API format
            elif hasattr(response, 'output') and response.output:
                if isinstance(response.output, list):
                    for output_item in response.output:
                        if hasattr(output_item, 'type') and output_item.type == 'function_call':
                            tool_calls.append({
                                'id': getattr(output_item, 'call_id', 'unknown'),
                                'name': getattr(output_item, 'name', 'unknown'),
                                'arguments': getattr(output_item, 'arguments', '{}')
                            })

            return tool_calls
        except Exception as e:
            logger.error(f"Error extracting tool calls: {e}", exc_info=True)
            return []

    async def _track_response_quality(self, ai_message, context: Dict, response_content: str):
        """Track response quality metrics - integrates with existing analytics."""
        try:
            # Calculate basic quality metrics similar to frontend ResponseQuality component
            has_code = bool(self._extract_code_snippets(response_content))
            has_structure = any(marker in response_content for marker in ['•', '1.', '##', '-'])
            has_citations = bool(context.get('chunks', []))

            # Simple quality scoring
            relevance = 0.9 if has_citations else 0.7
            helpfulness = (0.3 if has_structure else 0) + (0.3 if has_code else 0) + (0.4 if len(response_content) > 200 else 0)
            completeness = min(len(response_content) / 500, 1) * 0.7 + (0.3 if has_structure else 0)

            # This could be sent to the analytics API or stored directly
            quality_data = {
                'message_id': ai_message.id,
                'session_id': ai_message.session_id,
                'relevance': relevance,
                'helpfulness': helpfulness,
                'completeness': completeness,
                'has_code': has_code,
                'has_structure': has_structure,
                'has_citations': has_citations,
                'response_length': len(response_content),
                'context_chunks': len(context.get('chunks', [])),
                'referenced_files': len(context.get('file_references', []))
            }

            logger.debug(f"Response quality metrics: {quality_data}")
            # TODO: Integrate with analytics API when ready for persistent storage

        except Exception as e:
            logger.warning(f"Failed to track response quality: {e}")

    async def generate_summary(self, session_id: int) -> str:
        """Generate chat session summary."""
        messages = self.db.query(ChatMessage).filter_by(
            session_id=session_id,
            is_deleted=False
        ).order_by(ChatMessage.id).all()

        if len(messages) < 3:
            return "Chat session with minimal activity"

        # Build summary prompt
        conversation_text = []
        for msg in messages[:20]:  # First 20 messages
            role = "User" if msg.role == "user" else "AI"
            conversation_text.append(f"{role}: {msg.content[:200]}...")

        prompt = f"""Summarize this chat session in 2-3 sentences:

{chr(10).join(conversation_text)}

Focus on the main topics discussed and any key outcomes."""

        # Get runtime configuration for summary generation
        runtime_config = llm_client._get_runtime_config()

        response = await llm_client.complete(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,  # Keep lower temperature for summaries
            max_tokens=100  # Keep specific limit for summaries
        )

        return response
