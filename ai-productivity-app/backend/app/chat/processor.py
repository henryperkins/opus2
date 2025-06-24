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
        # Get runtime configuration for context management
        runtime_config = llm_client._get_runtime_config()
        max_context_tokens = runtime_config.get("maxTokens", settings.max_context_tokens)
        
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
                temperature=runtime_config.get("temperature"),  # Use runtime config
                stream=False,
                tools=llm_tools.TOOL_SCHEMAS,
                reasoning=settings.enable_reasoning,
                max_tokens=runtime_config.get("maxTokens"),  # Use runtime config
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
                    temperature=runtime_config.get("temperature"),  # Use runtime config
                    stream=False,
                    max_tokens=runtime_config.get("maxTokens"),  # Use runtime config
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
