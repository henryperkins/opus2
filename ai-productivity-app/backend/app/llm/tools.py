"""LLM *tool* registry and dispatcher.

This module exposes a small set of *functions* that the model can invoke via
the Chat Completions "tool calling" or the Azure Responses API MCP mechanism.

Each tool has two artefacts:

1. A JSON-schema (OpenAI function schema) describing its signature that is
   forwarded to the model under the **tools** parameter.
2. A Python implementation that performs the requested action and returns a
   *JSON-serialisable* result.

The dispatcher (``call_tool``) executes the correct implementation based on
the *name* coming back from the LLM.
"""

from __future__ import annotations

from typing import Any, Dict, List, Callable

import json
import logging

# Accept both sync & async sessions but prefer AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.context_builder import ContextBuilder
from app.chat.commands import ExplainCommand, GenerateTestsCommand
from app.llm.client import llm_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schemas – forwarded to the LLM verbatim
# ---------------------------------------------------------------------------


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "name": "file_search",
        "description": "Return the most relevant code snippets for a natural-language query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language search query"},
                "project_id": {"type": "integer", "description": "Current project identifier"},
                "k": {"type": "integer", "description": "Max number of snippets", "default": 5},
            },
            "required": ["query", "project_id"],
        },
    },
    {
        "type": "function",
        "name": "explain_code",
        "description": "Explain the purpose and behaviour of a code fragment identified by symbol name or file:line reference.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Symbol name or file_path:line"},
                "project_id": {"type": "integer"},
            },
            "required": ["location", "project_id"],
        },
    },
    {
        "type": "function",
        "name": "generate_tests",
        "description": "Generate unit tests for a function or class symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Name of the function or class"},
                "project_id": {"type": "integer"},
            },
            "required": ["symbol", "project_id"],
        },
    },
    {
        "type": "function",
        "name": "similar_code",
        "description": "Retrieve code snippets that are embedding-similar to the provided chunk identifier.",
        "parameters": {
            "type": "object",
            "properties": {
                "chunk_id": {"type": "integer"},
                "k": {"type": "integer", "default": 3},
            },
            "required": ["chunk_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _extract_llm_response_content(response: Any) -> str:
    """Extract text content from LLM response (both Chat Completions and Responses API)."""
    # Azure Responses API format
    if hasattr(response, 'output') and response.output:
        for item in response.output:
            if hasattr(item, 'content') and item.content:
                if isinstance(item.content, str):
                    return item.content
                # Handle structured content
                elif isinstance(item.content, list) and item.content:
                    text_parts = []
                    for content_item in item.content:
                        if hasattr(content_item, "text"):
                            text_parts.append(content_item.text)
                    return "\n".join(text_parts) if text_parts else str(item.content[0])
                else:
                    return str(item.content)
    
    # OpenAI Chat Completions format
    if hasattr(response, 'choices') and response.choices:
        return response.choices[0].message.content or ""
    
    # Legacy format
    if hasattr(response, 'output_text'):
        return response.output_text or ""
    
    # Fallback
    return str(response)


async def _tool_file_search(args: Dict[str, Any], db: Session | AsyncSession) -> Dict[str, Any]:
    query: str = args["query"]
    project_id: int = int(args["project_id"])
    k: int = int(args.get("k", 5))

    ctx_builder = ContextBuilder(db)  # type: ignore[arg-type]
    ctx = await ctx_builder.extract_context(query, project_id)
    chunks = ctx.get("chunks", [])[:k]
    return {"chunks": chunks}


async def _tool_explain_code(args: Dict[str, Any], db: Session | AsyncSession) -> Dict[str, Any]:
    location: str = args["location"].strip()
    project_id: int = int(args["project_id"])

    # Re-use existing ExplainCommand logic to build the prompt, then call LLM.
    cmd = ExplainCommand()
    cmd_result = await cmd.execute(location, {"project_id": project_id, "chunks": []}, db)

    if not cmd_result.get("success"):
        return {"error": cmd_result.get("message", "Unable to generate explanation")}

    prompt = cmd_result["prompt"]
    response = await llm_client.complete(
        messages=[{"role": "user", "content": prompt}], 
        stream=False
    )
    
    explanation = _extract_llm_response_content(response)
    return {"explanation": explanation}


async def _tool_generate_tests(args: Dict[str, Any], db: Session | AsyncSession) -> Dict[str, Any]:
    symbol: str = args["symbol"].strip()
    project_id: int = int(args["project_id"])

    cmd = GenerateTestsCommand()
    cmd_result = await cmd.execute(symbol, {"project_id": project_id, "chunks": []}, db)

    if not cmd_result.get("success"):
        return {"error": cmd_result.get("message", "Unable to create tests")}

    prompt = cmd_result["prompt"]
    response = await llm_client.complete(
        messages=[{"role": "user", "content": prompt}], 
        stream=False
    )
    
    tests = _extract_llm_response_content(response)
    return {"tests": tests}


async def _tool_similar_code(args: Dict[str, Any], db: Session | AsyncSession) -> Dict[str, Any]:
    from app.models.code import CodeEmbedding, CodeDocument  # local import to avoid circular
    from sqlalchemy import select

    chunk_id: int = int(args["chunk_id"])
    k: int = int(args.get("k", 3))

    # Handle both sync and async sessions
    if isinstance(db, AsyncSession):
        # Async version
        target_stmt = select(CodeEmbedding).where(CodeEmbedding.id == chunk_id)
        result = await db.execute(target_stmt)
        target = result.scalar_one_or_none()
        
        if not target or not target.embedding:
            return {"error": "chunk not found or embedding missing"}

        # Get neighbouring chunks from the same document
        neighbours_stmt = (
            select(CodeEmbedding)
            .where(
                CodeEmbedding.document_id == target.document_id,
                CodeEmbedding.id != target.id,
            )
            .order_by(CodeEmbedding.start_line)
            .limit(k)
        )
        result = await db.execute(neighbours_stmt)
        neighbours = result.scalars().all()
    else:
        # Sync version (legacy)
        target = db.query(CodeEmbedding).filter_by(id=chunk_id).first()
        if not target or not target.embedding:
            return {"error": "chunk not found or embedding missing"}

        neighbours = (
            db.query(CodeEmbedding)
            .filter(
                CodeEmbedding.document_id == target.document_id,
                CodeEmbedding.id != target.id,
            )
            .order_by(CodeEmbedding.start_line)
            .limit(k)
            .all()
        )

    out = []
    for n in neighbours:
        out.append(
            {
                "file_path": n.document.file_path,
                "start_line": n.start_line,
                "end_line": n.end_line,
                "content": n.chunk_content,
            }
        )

    return {"similar": out}


_HANDLERS: Dict[str, Callable[[Dict[str, Any], Session | AsyncSession], Any]] = {
    "file_search": _tool_file_search,
    "explain_code": _tool_explain_code,
    "generate_tests": _tool_generate_tests,
    "similar_code": _tool_similar_code,
}


async def call_tool(name: str, arguments: Dict[str, Any], db: Session | AsyncSession) -> Dict[str, Any]:
    """Execute *name* tool with *arguments* and return result."""

    handler = _HANDLERS.get(name)
    if not handler:
        logger.warning("Unknown tool requested: %s", name)
        return {"error": f"Tool '{name}' not available"}

    try:
        return await handler(arguments, db)
    except Exception as exc:  # noqa: BLE001
        logger.error("Tool '%s' failed: %s", name, exc, exc_info=True)
        return {"error": str(exc)}
