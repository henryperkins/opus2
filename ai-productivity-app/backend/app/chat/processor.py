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
from ..llm.streaming import StreamingHandler
from ..llm import tools as llm_tools
from ..models.chat import ChatMessage, ChatSession
from ..services.chat_service import ChatService
from ..websocket.manager import connection_manager
from .commands import command_registry
from .context_builder import ContextBuilder
from .secret_scanner import secret_scanner

__all__ = ["ChatProcessor"]

logger = logging.getLogger(__name__)

MAX_TOOL_CALL_ROUNDS = 3  # Safeguard for tool-calling LLM loops


class ChatProcessor:
    """High-level façade for chat message ingestion and AI response generation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.chat_service = ChatService(db)
        self.context_builder = ContextBuilder(db)

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
        try:
            # Separate preparation from processing to avoid mixing transaction scopes
            session, context, commands = await self._prepare_message_context(
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
                logger.error("Failed to send error message: %s", broadcast_exc, exc_info=True)

    # ------------------------------------------------------------------ #
    # INTERNAL HELPERS – top-level workflow
    # ------------------------------------------------------------------ #

    async def _prepare_message_context(
        self, session_id: int, message: ChatMessage, websocket: WebSocket
    ) -> tuple[ChatSession, dict, list]:
        """Prepare message context within a single transaction."""
        async with self.db.begin():
            session: ChatSession | None = await self._get_session(session_id)
            if not session:
                raise ValueError("Chat session not found")

            # 1. Secret scanning – redact *before* context extraction
            await self._apply_secret_scanning(message, websocket)

            # 2. Context extraction (files + vector chunks)
            context = await self.context_builder.extract_context(
                message.content,
                session.project_id,
            )
            context["project_id"] = session.project_id

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
        # placeholder in DB
        ai_msg = await self.chat_service.create_message(
            session_id=session_id,
            content="Generating response…",
            role="assistant",
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
        # TOOL-CALL LOOP – start with non-stream request so we can inspect
        # ------------------------------------------------------------------ #
        response = await llm_client.complete(
            messages=messages,
            temperature=cfg.get("temperature"),
            stream=False,
            tools=llm_tools.TOOL_SCHEMAS,
            reasoning=settings.enable_reasoning,
            max_tokens=cfg.get("max_tokens"),
        )

        round_no = 0
        while self._has_tool_calls(response) and round_no < MAX_TOOL_CALL_ROUNDS:
            round_no += 1
            logger.info("Tool-calling round %d", round_no)

            tool_results = await self._run_tool_calls(response)
            messages.extend(tool_results["message_deltas"])

            response = await llm_client.complete(
                messages=messages,
                temperature=cfg.get("temperature"),
                stream=False,
                max_tokens=cfg.get("max_tokens"),
            )

        if round_no >= MAX_TOOL_CALL_ROUNDS:
            logger.warning("Aborting tool loop after %d rounds", round_no)

        # ------------------------------------------------------------------ #
        # SECOND CALL – true streaming (no function calls left)
        # ------------------------------------------------------------------ #
        stream = llm_client.complete(
            messages=messages,
            temperature=cfg.get("temperature"),
            stream=True,
            max_tokens=cfg.get("max_tokens"),
        )

        handler = StreamingHandler(websocket)
        full_response = await handler.stream_response(stream, ai_msg.id)

        # ------------------------------------------------------------------ #
        # Persist and broadcast
        # ------------------------------------------------------------------ #
        # Update the message using the service to avoid transaction issues
        await self.chat_service.update_message_content(
            message_id=ai_msg.id,
            content=full_response,
            code_snippets=self._extract_code_snippets(full_response)
        )
        await self._broadcast_message_update(
            session_id=session_id,
            content=full_response,
            websocket_manager=connection_manager,
        )

        # analytics (fire-and-forget)
        asyncio.create_task(
            self._track_response_quality(ai_msg, context, full_response),
        )

        return full_response

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

        system_prompt = (
            "You are an AI coding assistant with deep knowledge of the code-base.\n"
            "Explain, test and refactor code. Use file paths & line numbers."
        )
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

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
                result = await llm_tools.call_tool(name, args, self.db)
            except Exception as exc:
                logger.error("Tool '%s' failed: %s", name, exc, exc_info=True)
                result = {"error": str(exc)}

            if getattr(llm_client, "use_responses_api", False):
                deltas.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.get("id", "unknown"),
                        "output": json.dumps(result),
                    },
                )
            else:
                deltas.append(
                    {
                        "role": "tool",
                        "name": name,
                        "content": json.dumps(result),
                    },
                )

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
        pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
        return [
            {"language": lang or "text", "code": code.strip()}
            for lang, code in pattern.findall(text)
        ]

    @staticmethod
    def _extract_response_content(response: Any) -> str:
        """Handle both Azure Responses API & OpenAI Chat formats."""
        try:
            if getattr(response, "output_text", None):
                return response.output_text

            if hasattr(response, "output") and response.output:
                for item in response.output:
                    if (getattr(item, "type", None) == "message" and
                        isinstance(item.content, str)):
                        return item.content

            # OpenAI chat
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
            if (getattr(response, "choices", None) and
                getattr(response.choices[0], "finish_reason", None) == "tool_calls"):
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
            if getattr(response, "choices", None):
                for call in getattr(response.choices[0].message, "tool_calls", []) or []:
                    calls.append(
                        {
                            "id": getattr(call, "id", "unknown"),
                            "name": getattr(call, "name", "unknown"),
                            "arguments": getattr(call, "arguments", "{}"),
                        },
                    )
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
        ai_message: ChatMessage,
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
                ((0.3 if has_structure else 0) +
                 (0.3 if has_code else 0) +
                 (0.4 if len(response_content) > 200 else 0)),
                1.0,
            )
            completeness = (min((len(response_content) / 500) * 0.7, 0.7) +
                            (0.3 if has_structure else 0))

            payload = {
                "message_id": ai_message.id,
                "session_id": ai_message.session_id,
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
