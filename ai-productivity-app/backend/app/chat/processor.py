from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import WebSocket
import logging
import asyncio

from app.models.chat import ChatSession, ChatMessage
from app.models.project import Project
from app.services.chat_service import ChatService
from app.llm.client import llm_client
from app.llm.streaming import StreamingHandler
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
            response_stream = await llm_client.complete(
                messages=messages,
                stream=True,
                temperature=0.7
            )

            full_response = await streaming_handler.stream_response(
                response_stream,
                ai_message.id
            )

            # Update message with full response
            ai_message.content = full_response

            # Extract code snippets from response
            code_snippets = self._extract_code_snippets(full_response)
            if code_snippets:
                ai_message.code_snippets = code_snippets

            self.db.commit()

        except Exception as e:
            logger.error(f"AI generation error: {e}")
            ai_message.content = "I apologize, but I encountered an error generating a response."
            self.db.commit()

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
