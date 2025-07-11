"""Extract code & conversation context for LLM prompts (async-ready).

The original implementation was synchronous and therefore incompatible with
`AsyncSession` – calling it with `await` inside :pyclass:`ChatProcessor` raised

    TypeError: object dict can't be used in 'await' expression

This rewrite keeps the public API the same but makes the *database touching*
methods truly **async** so they can be awaited from the processor while still
re-using the helper regex logic from the earlier version.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeDocument, CodeEmbedding
from app.models.chat import ChatMessage
from app.services.content_filter import content_filter

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Async helper that extracts relevant context for an LLM call."""

    FILE_PATTERN = re.compile(
        r"(?:^|[\s`\"])([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)(?:[:,]?\s*(?:line\s*)?(\d+))?"
    )
    CODE_BLOCK_PATTERN = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
    SYMBOL_PATTERN = re.compile(
        r"(?:function|class|def|interface|type)\s+([a-zA-Z_]\w*)"
    )

    def __init__(self, db: AsyncSession):
        self.db = db
        self.context_window = 50  # lines around reference

    # ------------------------------------------------------------------ #
    # High-level orchestration
    # ------------------------------------------------------------------ #

    async def extract_context(self, message: str, project_id: int) -> Dict[str, Any]:
        """Return dict with file refs, detected code blocks, symbols + chunks."""

        ctx: Dict[str, Any] = {
            "file_references": self.extract_file_references(message),
            "code_blocks": self.extract_code_blocks(message),
            "symbols": self.extract_symbols(message),
            "chunks": [],
        }

        # File reference → neighbouring chunks
        for file_ref in ctx["file_references"]:
            chunks = await self.get_file_context(
                project_id,
                file_ref["path"],
                file_ref.get("line"),
            )
            ctx["chunks"].extend(chunks)

        # Symbol search
        for symbol in ctx["symbols"]:
            chunks = await self.search_symbol(project_id, symbol)
            ctx["chunks"].extend(chunks[:3])

        # Deduplicate (document_id, start_line)
        seen: set[Tuple[int, int]] = set()
        uniq: List[Dict[str, Any]] = []
        for ch in ctx["chunks"]:
            key = (ch["document_id"], ch["start_line"])
            if key not in seen:
                seen.add(key)
                uniq.append(ch)

        # Apply final content filtering to all chunks
        filtered_chunks, final_warnings = content_filter.filter_and_validate_chunks(
            uniq
        )

        if final_warnings:
            logger.info(
                f"Final content filtering warnings: {'; '.join(final_warnings)}"
            )
            # Store warnings in context for potential user notification
            ctx["content_filter_warnings"] = final_warnings

        ctx["chunks"] = filtered_chunks
        return ctx

    # ------------------------------------------------------------------ #
    # Regex helpers (pure sync)
    # ------------------------------------------------------------------ #

    def extract_file_references(self, text: str) -> List[Dict[str, Any]]:
        refs: List[Dict[str, Any]] = []
        for m in self.FILE_PATTERN.finditer(text):
            file_path, line_num = m.group(1), m.group(2)
            if file_path.count(".") > 3 or file_path.startswith("http"):
                continue  # likely a URL / false positive
            refs.append(
                {
                    "path": file_path,
                    "line": int(line_num) if line_num else None,
                    "match": m.group(0),
                }
            )
        return refs

    def extract_code_blocks(self, text: str) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        for m in self.CODE_BLOCK_PATTERN.finditer(text):
            language = m.group(1) or "text"
            code = m.group(2).strip()
            blocks.append(
                {"language": language, "code": code, "length": len(code.split("\n"))}
            )
        return blocks

    def extract_symbols(self, text: str) -> List[str]:
        symbols: set[str] = set()
        for m in self.SYMBOL_PATTERN.finditer(text):
            symbols.add(m.group(1))

        for m in re.finditer(r"`([a-zA-Z_]\w*)`", text):
            name = m.group(1)
            if "_" in name or (name and name[0].isupper() and name[1:].islower()):
                symbols.add(name)
        return list(symbols)

    # ------------------------------------------------------------------ #
    # Database helpers – async
    # ------------------------------------------------------------------ #

    async def get_file_context(
        self,
        project_id: int,
        file_path: str,
        line_number: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return embedding chunks relevant to a file/line number."""
        # Exact match
        stmt = select(CodeDocument).where(
            CodeDocument.project_id == project_id, CodeDocument.file_path == file_path
        )
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()

        # Fallback: LIKE match (trailing path)
        if not doc:
            stmt = select(CodeDocument).where(
                CodeDocument.project_id == project_id,
                CodeDocument.file_path.like(f"%{file_path}"),
            )
            result = await self.db.execute(stmt)
            doc = result.scalar_one_or_none()

        if not doc:
            return []

        if line_number:
            c_stmt = select(CodeEmbedding).where(
                CodeEmbedding.document_id == doc.id,
                CodeEmbedding.start_line <= line_number,
                CodeEmbedding.end_line >= line_number,
            )
        else:
            c_stmt = (
                select(CodeEmbedding)
                .where(CodeEmbedding.document_id == doc.id)
                .order_by(CodeEmbedding.start_line)
                .limit(3)
            )

        chunks = (await self.db.execute(c_stmt)).scalars().all()
        formatted_chunks = [self._format_chunk(ch) for ch in chunks]

        # Filter chunks for sensitive content
        filtered_chunks, warnings = content_filter.filter_and_validate_chunks(
            formatted_chunks
        )

        if warnings:
            logger.info(
                f"Content filtering warnings for file context: {'; '.join(warnings)}"
            )

        return filtered_chunks

    async def search_symbol(self, project_id: int, symbol: str) -> List[Dict[str, Any]]:
        stmt = (
            select(CodeEmbedding)
            .join(CodeDocument, CodeDocument.id == CodeEmbedding.document_id)
            .where(
                CodeDocument.project_id == project_id,
                CodeEmbedding.symbol_name == symbol,
            )
        )
        result = await self.db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            stmt = (
                select(CodeEmbedding)
                .join(CodeDocument, CodeDocument.id == CodeEmbedding.document_id)
                .where(
                    CodeDocument.project_id == project_id,
                    CodeEmbedding.symbol_name.like(f"%{symbol}%"),
                )
                .limit(5)
            )
            result = await self.db.execute(stmt)
            chunks = result.scalars().all()

        formatted_chunks = [self._format_chunk(ch) for ch in chunks]

        # Filter chunks for sensitive content
        filtered_chunks, warnings = content_filter.filter_and_validate_chunks(
            formatted_chunks
        )

        if warnings:
            logger.info(
                f"Content filtering warnings for symbol search: {'; '.join(warnings)}"
            )

        return filtered_chunks

    async def build_conversation_context(
        self,
        session_id: int,
        *,
        max_messages: int = 20,
        max_tokens: int = 8_000,
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id, ChatMessage.is_deleted.is_(False)
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(max_messages)
        )
        msgs = (await self.db.execute(stmt)).scalars().all()

        ctx_msgs: List[Dict[str, Any]] = []
        total = 0
        for msg in reversed(msgs):
            est = len(msg.content) // 4
            if msg.code_snippets:
                for snip in msg.code_snippets:
                    if isinstance(snip, dict) and "code" in snip:
                        est += len(snip["code"]) // 4
            if ctx_msgs and total + est > max_tokens:
                break
            entry: Dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
                "id": msg.id,
                "created_at": msg.created_at.isoformat(),
                "tokens": est,
            }
            if msg.code_snippets:
                entry["code_snippets"] = msg.code_snippets
            if msg.referenced_files:
                entry["referenced_files"] = msg.referenced_files
            ctx_msgs.append(entry)
            total += est

        logger.debug(
            "Built conversation context: %d messages (~%d tokens)", len(ctx_msgs), total
        )
        return ctx_msgs

    async def get_conversation_summary(
        self, session_id: int, up_to_message_id: Optional[int] = None
    ) -> Optional[str]:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id, ChatMessage.is_deleted.is_(False)
            )
            .order_by(ChatMessage.created_at)
        )
        if up_to_message_id:
            stmt = stmt.where(ChatMessage.id < up_to_message_id)

        msgs = (await self.db.execute(stmt.limit(50))).scalars().all()
        if len(msgs) < 5:
            return None
        topics: List[str] = []
        for msg in msgs[-10:]:
            if msg.role == "user" and len(msg.content) > 50:
                topics.append(f"User asked: {msg.content[:100]}…")
            elif msg.role == "assistant" and msg.referenced_files:
                files = ", ".join(msg.referenced_files[:3])
                topics.append(f"Discussed files: {files}")
        return (
            f"Earlier conversation context: {'; '.join(topics[:5])}" if topics else None
        )

    async def create_timeline_event(
        self,
        *,
        project_id: int,
        event_type: str,
        content: str,
        referenced_files: Optional[List[str]] = None,
    ) -> None:
        """Fire-and-forget analytics entry – errors are swallowed."""
        try:
            from app.models.timeline import TimelineEvent

            ev = TimelineEvent(
                project_id=project_id,
                event_type=event_type,
                title="Chat Message",
                description=content[:200] + ("…" if len(content) > 200 else ""),
                event_metadata={
                    "preview": content[:100] + ("…" if len(content) > 100 else ""),
                    "referenced_files": referenced_files or [],
                },
            )
            self.db.add(ev)
            await self.db.commit()
        except Exception:  # noqa: BLE001 – best-effort only
            logger.debug("Timeline event creation failed", exc_info=True)

    # ------------------------------------------------------------------ #
    # Formatting helpers
    # ------------------------------------------------------------------ #

    def _format_chunk(self, chunk: CodeEmbedding) -> Dict[str, Any]:
        return {
            "document_id": chunk.document_id,
            "file_path": chunk.document.file_path if chunk.document else None,
            "language": chunk.document.language if chunk.document else None,
            "symbol_name": chunk.symbol_name,
            "symbol_type": chunk.symbol_type,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content": chunk.chunk_content,
        }
