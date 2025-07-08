"""processor.py – Chat message processing and orchestration

This module contains a single public class, ChatProcessor, which

1. validates and stores incoming user messages,
2. assembles conversational + code context,
3. performs tool/function-calling loops with the LLM,
4. streams the final reply back to every connected client, and
5. records analytics.

Key design points
-----------------
• Fully async: uses AsyncSession from SQLAlchemy, never blocks the event-loop.
• Transactional safety: a *single* transaction per user message – no partial state.
• WebSocket fan-out happens **after** the assistant reply is stored.
• Streaming fidelity: forwards the model’s native token stream; it never re-splits code
  fences, so markdown integrity is preserved.
• Dependency-injected: pass an AsyncSession; the class wires up its own lightweight
  collaborators (ChatService, ContextBuilder).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..llm.client import llm_client
from ..llm.streaming import StreamingHandler, EnhancedStreamingHandler
from ..llm import tools as llm_tools
from ..models.chat import ChatMessage, ChatSession
from ..services.chat_service import ChatService
from ..services.knowledge_service import KnowledgeService
from ..services.confidence_service import ConfidenceService
from ..services.unified_config_service import UnifiedConfigService
from ..embeddings.generator import EmbeddingGenerator
from ..websocket.manager import connection_manager
from .commands import command_registry
from .context_builder import ContextBuilder
from .secret_scanner import secret_scanner

__all__ = ["ChatProcessor"]

logger = logging.getLogger(__name__)

MAX_TOOL_CALL_ROUNDS = 3  # Safeguard for tool-calling LLM loops


class ChatProcessor:
    """High-level façade for chat message ingestion and AI response generation."""

    def __init__(self, db: AsyncSession, kb: KnowledgeService | None = None) -> None:
        self.db = db
        self.chat_service = ChatService(db)
        self.context_builder = ContextBuilder(db)
        self.confidence_service = ConfidenceService()
        self.config_service = UnifiedConfigService(db)
        self._kb = kb

    # --------------------------------------------------------------------- #
    # PUBLIC API
    # --------------------------------------------------------------------- #

    async def process_message(
        self,
        session_id: int,
        message: ChatMessage,
        websocket: WebSocket,
    ) -> None:
        """Validate, persist and respond to a **single** user message."""
        try:  # Separate preparation from processing to avoid mixing transaction scopes
            _, context, commands = await self._prepare_message_context(
                session_id, message, websocket
            )

            # Heavy LLM work happens outside any transaction
            if commands:
                await self._handle_command_results(
                    session_id=session_id,
                    commands=commands,
                    context=context,
                    websocket=websocket,
                )
            else:
                await self._respond_with_llm(
                    session_id=session_id,
                    prompt=message.content,
                    context=context,
                    websocket=websocket,
                )

        except Exception as exc:  # pragma: no cover (captured by middleware)
            logger.error("Message processing error: %s", exc, exc_info=True)
            try:
                await self.chat_service.create_message(
                    session_id=session_id,
                    content=f"Sorry, I hit an unexpected error: {exc}",
                    role="assistant",
                )
            except Exception as broadcast_exc:
                logger.error(
                    "Failed to send error message: %s", broadcast_exc, exc_info=True
                )

    # ------------------------------------------------------------------ #
    # INTERNAL HELPERS – top-level workflow
    # ------------------------------------------------------------------ #

    async def _prepare_message_context(
        self, session_id: int, message: ChatMessage, websocket: WebSocket
    ) -> tuple[ChatSession, dict, list]:
        """Prepare message context, separating DB writes from heavy I/O."""
        # Get session and scan for secrets (within existing session context)
        session: ChatSession | None = await self._get_session(session_id)
        if not session:
            raise ValueError("Chat session not found")

        # 1. Secret scanning – redact *before* context extraction
        await self._apply_secret_scanning(message, websocket)
        await self.db.flush()

        # Outside transaction: Heavy I/O for context building.
        # 2. Context extraction (files + vector chunks)
        context = await self.context_builder.extract_context(
            message.content,
            session.project_id,
        )
        context["project_id"] = session.project_id

        # 2a. Frontend context is now handled through structured fields
        # The metadata from WebSocket is decomposed into referenced_files, referenced_chunks, etc.
        # during message creation in ChatService.create_message()

        # 3. Knowledge base search with RAG tracking
        rag_metadata = {
            "rag_used": False,
            "rag_confidence": None,
            "knowledge_sources_count": 0,
            "search_query_used": None,
            "context_tokens_used": 0,
            "rag_status": "standard",
            "rag_error_message": None,
        }

        try:
            # Skip knowledge search if service is unavailable
            if self._kb is None:
                raise Exception("Knowledge service not available")

            kb_hits = await self._kb.search_knowledge(
                query=message.content,
                project_ids=[session.project_id],
                limit=10,
            )

            # Extract entry IDs for context building
            entry_ids = [result["id"] for result in kb_hits]

            # Build knowledge context with token limits
            if entry_ids:
                ctx_kb = await self._kb.build_context(
                    max_context_length=getattr(settings, "model_ctx", 4000) - 1024,
                    db=self.db,
                    search_results=kb_hits,
                )
                context["knowledge"] = ctx_kb["context"]
                context["citations"] = ctx_kb["citations"]

                # Update RAG metadata
                rag_metadata["rag_used"] = True
                rag_metadata["knowledge_sources_count"] = len(kb_hits)
                rag_metadata["search_query_used"] = message.content
                # Use unified token counting for consistency
                from app.utils.token_counter import count_tokens

                rag_metadata["context_tokens_used"] = count_tokens(ctx_kb["context"])

                # Calculate confidence score
                confidence = self.confidence_service.calculate_rag_confidence(kb_hits)
                rag_metadata["rag_confidence"] = confidence
                rag_metadata["rag_status"] = (
                    self.confidence_service.calculate_degradation_status(
                        confidence, kb_hits
                    )
                )
            else:
                # No knowledge base hits - keep RAG as unused and standard status
                context["knowledge"] = ""
                context["citations"] = {}
                # Don't set rag_status here - leave it as "standard" since RAG wasn't used

            # Store RAG metadata in context for later use
            context["rag_metadata"] = rag_metadata

        except Exception as exc:
            # Log the full exception with traceback for debugging
            logger.error("Knowledge base search failed: %s", exc, exc_info=True)
            context["knowledge"] = ""
            context["citations"] = {}

            # ------------------------------------------------------------- #
            # Differentiate between *expected* configuration gaps
            # (knowledge base disabled) and *real* runtime errors. Only the
            # latter should surface as a RAG error in the UI.
            #
            # IMPORTANT: Only set error status for genuine failures that should
            # be shown to users. For configuration issues, keep rag_used=False
            # and rag_status="standard" to avoid confusing UI indicators.
            # ------------------------------------------------------------- #
            exc_str = str(exc)
            if "Knowledge service not available" in exc_str:
                # Gracefully degrade when KB is not configured – treat as
                # standard mode so the UI doesn't show error indicators
                # when RAG is simply not enabled
                rag_metadata["rag_status"] = "standard"  # Changed from "inactive"
                rag_metadata["rag_error_message"] = None
            elif "Connection refused" in exc_str or "[Errno 111]" in exc_str:
                # Service is expected but unreachable → genuine error
                rag_metadata["rag_status"] = "error"
                rag_metadata["rag_error_message"] = "Knowledge base service unavailable"
                logger.error("Qdrant connection failed: %s", exc)
            elif "QdrantException" in type(exc).__name__:
                # Qdrant-specific errors - preserve more context
                rag_metadata["rag_status"] = "error"
                rag_metadata["rag_error_message"] = f"Search error: {exc_str[:100]}"
                logger.error("Qdrant search error: %s", exc)
            elif "timeout" in exc_str.lower():
                # Timeout errors
                rag_metadata["rag_status"] = "error"
                rag_metadata["rag_error_message"] = "Search timeout"
                logger.error("Knowledge search timeout: %s", exc)
            else:
                # Fallback for unexpected failures - preserve some context
                rag_metadata["rag_status"] = "error"
                error_summary = exc_str[:50] if exc_str else type(exc).__name__
                rag_metadata["rag_error_message"] = f"Search failed: {error_summary}"
                logger.error("Unexpected knowledge search error: %s", exc)

            context["rag_metadata"] = rag_metadata

        # Persist context references, timeline event, and command details.
        message = await self.db.merge(message)
        message.referenced_files = [
            ref["path"] for ref in context.get("file_references", [])
        ]
        message.referenced_chunks = [
            c["document_id"] for c in context.get("chunks", [])
        ]

        # 3. Timeline analytics
        await self.context_builder.create_timeline_event(
            project_id=session.project_id,
            event_type="chat_message",
            content=message.content,
            referenced_files=message.referenced_files,
        )

        # 4. Slash-command execution
        commands = await command_registry.execute_commands(
            message.content,
            context,
            self.db,
        )
        if commands:
            message.applied_commands = {
                cmd["command"]: cmd.get("prompt", cmd.get("message", ""))
                for cmd in commands
            }

        # Commit the changes
        await self.db.commit()

        return session, context, commands or []

    async def _handle_command_results(
        self,
        *,
        session_id: int,
        commands: List[Dict[str, Any]],
        context: Dict[str, Any],
        websocket: WebSocket,
    ) -> None:
        """Iterate over completed slash commands and act on each result."""

        for cmd in commands:
            if cmd.get("requires_llm"):
                full_txt = await self._respond_with_llm(
                    session_id=session_id,
                    prompt=cmd["prompt"],
                    context=context,
                    websocket=websocket,
                )
            else:
                msg = await self.chat_service.create_message(
                    session_id=session_id,
                    content=cmd["message"],
                    role="assistant",
                    rag_metadata=context.get("rag_metadata", {}),
                )
                full_txt = msg.content

            # push update for *every* assistant addition
            await self._broadcast_message_update(
                session_id=session_id,
                content=full_txt,
                websocket_manager=connection_manager,
            )

    async def _respond_with_llm(
        self,
        *,
        session_id: int,
        prompt: str,
        context: Dict[str, Any],
        websocket: WebSocket,
    ) -> str:
        """End-to-end LLM orchestration plus streaming."""
        # placeholder in DB (don't broadcast yet - streaming will handle it)
        ai_msg = await self.chat_service.create_message(
            session_id=session_id,
            content="Generating response…",
            role="assistant",
            rag_metadata=context.get("rag_metadata", {}),
            broadcast=False,
        )

        # build prompt messages
        messages, _ = await self._assemble_llm_messages(
            session_id=session_id,
            prompt=prompt,
            context=context,
        )

        # pick runtime cfg once (thread-safe snapshot)
        cfg = llm_client._get_runtime_config()

        # ------------------------------------------------------------------ #
        # ENHANCED STREAMING – single-pass with tools enabled
        # Apply o3/o4-mini guidance: don't induce additional reasoning for reasoning models
        # ------------------------------------------------------------------ #

        # Check if we're using a reasoning model to adjust parameters
        active_model = cfg.get("chat_model", llm_client.active_model)
        is_reasoning_model = (
            llm_client._is_reasoning_model(active_model)
            if hasattr(llm_client, "_is_reasoning_model")
            else False
        )

        # Apply tool limits based on OpenAI guidance (ideally <100 tools for best performance)
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
                self.config_service.get_current_config().enable_reasoning if not is_reasoning_model else None
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

        # ------------------------------------------------------------------ #
        # Add confidence warnings if needed
        # ------------------------------------------------------------------ #
        enhanced_response = await self._add_confidence_warnings(full_response, context)
        
        # ------------------------------------------------------------------ #
        # Persist and broadcast
        # ------------------------------------------------------------------ #
        # Update the message using the service to avoid transaction issues
        await self.chat_service.update_message_content(
            message_id=ai_msg.id,
            content=enhanced_response,
            code_snippets=self._extract_code_snippets(enhanced_response),
            broadcast=True,  # This will be the only broadcast for this message
        )

        # analytics (fire-and-forget)
        asyncio.create_task(
            self._track_response_quality(
                ai_msg.id, ai_msg.session_id, context, full_response
            ),
        )

        return enhanced_response

    async def _add_confidence_warnings(
        self, response: str, context: Dict[str, Any]
    ) -> str:
        """Add confidence warnings to response if needed."""
        rag_metadata = context.get("rag_metadata", {})
        
        if not rag_metadata.get("rag_used", False):
            # No RAG was used - add a general disclaimer for knowledge-based questions
            if self._seems_like_knowledge_question(response):
                warning = (
                    "\n\n*Note: This response is based on general knowledge rather than "
                    "specific documentation from your codebase. For the most accurate "
                    "and up-to-date information, please check your project documentation.*"
                )
                return response + warning
            return response
            
        rag_confidence = rag_metadata.get("rag_confidence")
        rag_status = rag_metadata.get("rag_status", "standard")
        knowledge_sources_count = rag_metadata.get("knowledge_sources_count", 0)
        
        warnings = []
        
        # Low confidence warnings
        if rag_confidence is not None:
            if rag_confidence < 0.3:
                warnings.append(
                    "⚠️ **Low Confidence**: This response is based on limited or potentially "
                    "irrelevant sources from your codebase."
                )
            elif rag_confidence < 0.6:
                warnings.append(
                    "⚠️ **Moderate Confidence**: This response may not be fully comprehensive. "
                    "Consider checking additional sources."
                )
                
        # Status-based warnings
        if rag_status == "poor":
            warnings.append(
                "⚠️ **Limited Sources**: Very few relevant sources were found in your codebase."
            )
        elif rag_status == "degraded":
            warnings.append(
                "⚠️ **Quality Notice**: The available sources may not be the most authoritative."
            )
        elif rag_status == "error":
            warnings.append(
                "⚠️ **Search Error**: There was an issue retrieving information from your codebase."
            )
            
        # Source count warnings
        if knowledge_sources_count == 0:
            warnings.append(
                "⚠️ **No Sources**: This response is based on general knowledge only."
            )
        elif knowledge_sources_count == 1:
            warnings.append(
                "ℹ️ **Single Source**: This response is based on only one source from your codebase."
            )
            
        # Content filtering warnings
        if context.get("content_filter_warnings"):
            warnings.append(
                "ℹ️ **Content Filtered**: Some sensitive content was filtered from the sources."
            )
            
        if warnings:
            warning_text = "\n\n---\n\n" + "\n\n".join(warnings)
            return response + warning_text
            
        return response
        
    def _seems_like_knowledge_question(self, response: str) -> bool:
        """Heuristic to detect if a question seems like it needs specific knowledge."""
        # Check if response contains general disclaimers or seems to lack specific details
        general_phrases = [
            "generally", "typically", "usually", "in most cases", 
            "it depends", "you should", "you might want to",
            "without seeing", "without knowing", "would need to see"
        ]
        
        response_lower = response.lower()
        
        # Count general phrases
        general_count = sum(1 for phrase in general_phrases if phrase in response_lower)
        
        # If response is short and has many general phrases, it's probably general knowledge
        return len(response) < 500 and general_count >= 2

    # ------------------------------------------------------------------ #
    # INTERNAL HELPERS – smaller pieces
    # ------------------------------------------------------------------ #

    async def _get_session(self, session_id: int) -> ChatSession | None:
        """Async helper to load a session row."""
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _apply_secret_scanning(
        self,
        message: ChatMessage,
        websocket: WebSocket,
    ) -> None:
        """Detect & redact secrets in-place and notify the user via WS."""
        scan = secret_scanner.validate_message(message.content)
        if scan["valid"]:
            return

        message.content = secret_scanner.redact(message.content, scan["findings"])

        await websocket.send_json(
            {
                "type": "warning",
                "message": f"Secrets found and redacted: {scan['message']}",
            },
        )

    async def _assemble_llm_messages(
        self,
        *,
        session_id: int,
        prompt: str,
        context: Dict[str, Any],
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Return (`messages`, `conversation_history`)."""
        cfg = llm_client._get_runtime_config()
        max_ctx = cfg.get("max_tokens", settings.max_context_tokens)
        avail_ctx = int(max_ctx * 0.6)

        conversation = await self.context_builder.build_conversation_context(
            session_id=session_id,
            max_tokens=avail_ctx // 2,
        )

        # Apply o3/o4-mini prompting best practices: clear context and role definition
        system_prompt = (
            "You are an AI coding assistant with deep knowledge of this codebase. "
            "Your role is to help users understand, modify, and improve their code.\n\n"
            "Key guidelines:\n"
            "- Be proactive in using available tools to accomplish the user's goals\n"
            "- Use file paths and line numbers when referencing code\n"
            "- Don't stop at the first failure - try alternative approaches\n"
            "- Provide clear, actionable explanations and suggestions\n"
            "- When generating tests, ensure comprehensive coverage of edge cases"
        )
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # -------------------------------------------------------------- #
        # Knowledge-base context
        # -------------------------------------------------------------- #
        if context.get("knowledge"):
            messages.append(
                {
                    "role": "system",
                    "content": self._format_knowledge_context(context),
                }
            )

        # optional conversation summary
        if len(conversation) >= 15:
            oldest_id = conversation[0]["id"]
            summary = await self.context_builder.get_conversation_summary(
                session_id=session_id,
                up_to_message_id=oldest_id,
            )
            if summary:
                messages.append(
                    {"role": "system", "content": f"Previous summary: {summary}"},
                )

        # code embeddings
        if context.get("chunks"):
            code_ctx = llm_client.prepare_code_context(context["chunks"])
            messages.append(
                {"role": "system", "content": f"Relevant code context:\n{code_ctx}"},
            )

        # historical dialogue
        for msg in conversation:
            content = msg["content"]

            if msg.get("referenced_files"):
                files = ", ".join(msg["referenced_files"][:3])
                content += f" [files: {files}]"

            messages.append({"role": msg["role"], "content": content})

        # current user prompt
        messages.append({"role": "user", "content": prompt})

        logger.debug(
            "LLM context: %s messages, %s code chunks",
            len(messages),
            len(context.get("chunks", [])),
        )
        return messages, conversation

    # ------------------------------------------------------------------ #
    # Utility: format knowledge context into a well-structured markdown
    # ------------------------------------------------------------------ #

    @staticmethod
    def _format_knowledge_context(ctx: dict) -> str:
        """Return a Markdown string containing KB snippets with citations.

        Enhanced formatting that handles both database knowledge and frontend context.
        Includes proper sectioning for documents and code snippets.
        """
        lines: list[str] = [
            "You have access to the following knowledge base information. Use it to provide accurate, contextual responses.",
            "",
        ]

        # Handle citations from knowledge service (backend)
        citations: dict = ctx.get("citations", {})
        if citations:
            lines.extend(
                [
                    "## Knowledge Base Results",
                    "",
                ]
            )

            for marker, meta in citations.items():
                title = meta.get("title", "Document")
                src = meta.get("source", "unknown")
                content = (
                    meta.get("excerpt") or ctx["knowledge"].split(marker, 1)[1].strip()
                )

                lines.append(f"### {marker} {title}")
                lines.append(f"**Source:** {src}")
                lines.append(f"**Content:** {content}")
                lines.append("")

        # Handle direct knowledge content
        knowledge_content = ctx.get("knowledge", "")
        if knowledge_content and not citations:
            lines.extend(
                [
                    "## Relevant Information",
                    "",
                    knowledge_content,
                    "",
                ]
            )

        # Handle structured context from frontend (user selections)
        frontend_context = ctx.get("frontend_context", [])
        if frontend_context:
            lines.extend(
                [
                    "## Selected Context Items",
                    "",
                ]
            )

            for idx, item in enumerate(frontend_context, 1):
                item_type = item.get("type", "document")
                source = item.get("source", "Unknown source")
                content = item.get("content", "")
                relevance = item.get("relevance", 0.0)

                lines.append(f"### [{idx}] {item_type.title()} - {source}")
                lines.append(f"**Relevance:** {relevance:.2f}")

                if item.get("language") and item_type == "code":
                    lines.append(f"**Language:** {item['language']}")
                    lines.append(f"```{item['language']}")
                    lines.append(content)
                    lines.append("```")
                else:
                    lines.append(f"**Content:** {content}")
                lines.append("")

        return "\n".join(lines) if len(lines) > 2 else ""

    async def _run_tool_calls(
        self,
        response: Any,
    ) -> Dict[str, Any]:
        """Execute tool calls requested by the model and return new message deltas."""
        deltas: list[dict[str, Any]] = []

        for call in self._extract_tool_calls(response):
            name = call["name"]
            try:
                args = json.loads(call["arguments"])
            except Exception as exc:
                logger.error("Tool call argument JSON decode failed: %s", exc)
                args = {}

            logger.info("Calling tool %s with %s", name, args)
            try:
                result = await asyncio.wait_for(
                    llm_tools.call_tool(name, args, self.db),
                    timeout=getattr(settings, "tool_timeout", 30),
                )
            except asyncio.TimeoutError:
                logger.error(
                    "Tool '%s' timed out after %s seconds",
                    name,
                    getattr(settings, "tool_timeout", 30),
                )
                result = {
                    "success": False,
                    "error": f"Tool execution timed out after {getattr(settings, 'tool_timeout', 30)} seconds",
                    "error_type": "timeout",
                }
            except Exception as exc:
                logger.error("Tool '%s' failed: %s", name, exc, exc_info=True)
                result = {
                    "success": False,
                    "error": str(exc),
                    "error_type": "execution_exception",
                }

            # Format result for API following OpenAI documentation
            formatted_output = llm_tools.format_tool_result_for_api(result)

            if getattr(llm_client, "use_responses_api", False):
                # Azure Responses API format for function call results
                deltas.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.get("id", "unknown"),
                        "output": formatted_output,
                    },
                )
            else:
                # Standard Chat Completions API format for tool results
                deltas.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id", "unknown"),
                        "name": name,
                        "content": formatted_output,
                    },
                )

        return {"message_deltas": deltas}

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

    @staticmethod
    async def _broadcast_message_update(
        *,
        session_id: int,
        content: str,
        websocket_manager: Any,
    ) -> None:
        """Send the final assistant text to *all* clients in the session."""
        try:
            await websocket_manager.send_message(
                {
                    "type": "message_update",
                    "updates": {"content": content, "edited": False},
                },
                session_id,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("WebSocket broadcast failed: %s", exc)

    # ------------------------------------------------------------------ #
    # UTILITY – extraction helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_code_snippets(text: str) -> List[Dict[str, str]]:
        """Return a list of fenced code blocks with their languages."""
        pattern = re.compile(r"```(\w+)?[ \t]*\r?\n(.*?)```", re.DOTALL)
        return [
            {"language": lang or "text", "code": code.strip()}
            for lang, code in pattern.findall(text)
        ]

    @staticmethod
    def _extract_response_content(response: Any) -> str:
        """Handle both Azure Responses API & OpenAI Chat formats."""
        try:
            # Azure Responses API format
            if hasattr(response, "output") and response.output:
                # Log additional Responses API fields for debugging
                if logger.isEnabledFor(logging.DEBUG):
                    response_id = getattr(response, "id", "unknown")
                    status = getattr(response, "status", "unknown")
                    created_at = getattr(response, "created_at", "unknown")
                    logger.debug(
                        f"Responses API - ID: {response_id}, Status: {status}, Created: {created_at}"
                    )

                    if hasattr(response, "usage"):
                        logger.debug(f"Token usage: {response.usage}")

                # Extract content from output - handle o3 model responses
                for item in response.output:
                    if hasattr(item, "type") and item.type == "message":
                        if hasattr(item, "content"):
                            if isinstance(item.content, list):
                                # Handle list of content items
                                text_parts = []
                                for content_item in item.content:
                                    if hasattr(content_item, "text"):
                                        text_parts.append(content_item.text)
                                return " ".join(text_parts)
                            else:
                                return str(item.content)
                        elif hasattr(item, "text"):
                            # Direct text attribute
                            return item.text

            # Legacy output_text field
            if getattr(response, "output_text", None):
                return response.output_text

            # OpenAI Chat Completions format
            if getattr(response, "choices", None):
                return response.choices[0].message.content or ""

            logger.warning("Unknown response format: %s", type(response))
            return str(response)
        except Exception as exc:
            logger.error("Failed to extract response: %s", exc, exc_info=True)
            return "Error extracting response content"

    # ------------------------------------------------------------------ #
    # UTILITY – tool-call inspectors
    # ------------------------------------------------------------------ #

    @staticmethod
    def _has_tool_calls(response: Any) -> bool:
        try:
            if (
                getattr(response, "choices", None)
                and getattr(response.choices[0], "finish_reason", None) == "tool_calls"
            ):
                return True

            if hasattr(response, "output") and response.output:
                return any(
                    getattr(item, "type", None) == "function_call"
                    for item in response.output
                )
            return False
        except Exception:
            return False

    @staticmethod
    def _extract_tool_calls(response: Any) -> List[Dict[str, Any]]:
        calls: list[Dict[str, Any]] = []

        try:
            # Chat Completions API format
            if getattr(response, "choices", None):
                choice = response.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "tool_calls"):
                    for call in choice.message.tool_calls or []:
                        # Extract function details from nested structure
                        function_name = (
                            getattr(call.function, "name", "unknown")
                            if hasattr(call, "function")
                            else getattr(call, "name", "unknown")
                        )
                        function_args = (
                            getattr(call.function, "arguments", "{}")
                            if hasattr(call, "function")
                            else getattr(call, "arguments", "{}")
                        )

                        calls.append(
                            {
                                "id": getattr(call, "id", "unknown"),
                                "name": function_name,
                                "arguments": function_args,
                            },
                        )
            # Azure Responses API format
            elif hasattr(response, "output") and response.output:
                for item in response.output:
                    if getattr(item, "type", None) == "function_call":
                        calls.append(
                            {
                                "id": getattr(item, "call_id", "unknown"),
                                "name": getattr(item, "name", "unknown"),
                                "arguments": getattr(item, "arguments", "{}"),
                            },
                        )
        except Exception as exc:
            logger.error("Tool-call extraction failed: %s", exc, exc_info=True)
        return calls

    # ------------------------------------------------------------------ #
    # ANALYTICS
    # ------------------------------------------------------------------ #

    async def _track_response_quality(
        self,
        message_id: int,
        session_id: int,
        context: Dict[str, Any],
        response_content: str,
    ) -> None:
        """Store lightweight quality metrics (fire-and-forget)."""
        try:
            has_code = bool(self._extract_code_snippets(response_content))
            has_structure = any(mark in response_content for mark in ("•", "##", "- "))
            has_citations = bool(context.get("chunks"))

            relevance = 0.9 if has_citations else 0.7
            helpfulness = min(
                (
                    (0.3 if has_structure else 0)
                    + (0.3 if has_code else 0)
                    + (0.4 if len(response_content) > 200 else 0)
                ),
                1.0,
            )
            completeness = min((len(response_content) / 500) * 0.7, 0.7) + (
                0.3 if has_structure else 0
            )

            payload = {
                "message_id": message_id,
                "session_id": session_id,
                "relevance": relevance,
                "helpfulness": helpfulness,
                "completeness": min(completeness, 1.0),
                "has_code": has_code,
                "has_structure": has_structure,
                "has_citations": has_citations,
            }
            logger.debug("Quality metrics: %s", payload)
            # TODO: send to analytics backend
        except Exception as exc:  # broad-except fine in analytics stub
            logger.warning("Metric tracking failed: %s", exc)
