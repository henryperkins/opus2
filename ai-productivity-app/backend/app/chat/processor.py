from typing import Dict, List, Optional
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
        # Build conversation history
        conversation = self.context_builder.build_conversation_context(session_id)

        # Prepare messages for LLM
        messages = [
            {
                "role": "system",
                "content": """You are an AI coding assistant with access to the project codebase.
You can analyze code, explain functionality, generate tests, and help with development tasks.
Always provide clear, concise, and accurate responses.
When referencing code, mention the file path and line numbers."""
            }
        ]

        # Add code context if available
        if context['chunks']:
            code_context = llm_client.prepare_code_context(context['chunks'])
            messages.append({
                "role": "system",
                "content": code_context
            })

        # Add conversation history
        for msg in conversation[-5:]:  # Last 5 messages
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        # Add current prompt
        messages.append({
            "role": "user",
            "content": prompt
        })

        # Create placeholder message
        ai_message = await self.chat_service.create_message(
            session_id=session_id,
            content="",
            role='assistant'
        )

        # Stream response
        streaming_handler = StreamingHandler(websocket)

        try:
            # First non-stream call – we need body to inspect potential tool calls
            response = await llm_client.complete(
                messages=messages,
                temperature=0.7,
                stream=False,
                tools=llm_tools.TOOL_SCHEMAS,
                reasoning=settings.enable_reasoning,
            )

            # Loop while model wants to call tools – guard against empty
            # *choices* which can happen when running with the local stub
            # client in development / test environments.
            while (
                hasattr(response, "choices")
                and response.choices  # non-empty list
                and response.choices[0].finish_reason == "tool_calls"
            ):
                for tool_call in response.choices[0].message.tool_calls:
                    name = tool_call.name
                    args_json = json.loads(tool_call.arguments)

                    result = await llm_tools.call_tool(name, args_json, self.db)
                    messages.append({
                        "role": "tool",
                        "name": name,
                        "content": json.dumps(result),
                    })

                # ask LLM to continue with new context
                response = await llm_client.complete(
                    messages=messages,
                    temperature=0.7,
                    stream=False,
                )

            # final assistant content
            if hasattr(response, "choices") and response.choices:
                final_text = response.choices[0].message.content
            else:
                # Fallback – the local *openai* stub or unexpected provider
                # response.  Convert to string so the user receives *some*
                # feedback instead of a silent failure that triggers the
                # generic "LLM unavailable" error path below.
                final_text = str(response)

            # now stream it to client (simulate streaming)
            async def _generator():  # noqa: D401
                yield final_text

            full_response = await streaming_handler.stream_response(_generator(), ai_message.id)

            # Update message in DB
            ai_message.content = full_response

            code_snippets = self._extract_code_snippets(full_response)
            if code_snippets:
                ai_message.code_snippets = code_snippets

            self.db.commit()

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

        response = await llm_client.complete(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=100
        )

        return response
