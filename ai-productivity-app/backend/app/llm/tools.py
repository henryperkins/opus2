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
        "function": {
            "name": "file_search",
            "description": "Search and return the most relevant code snippets for a natural-language query. Use this when you need to find specific code patterns, functions, or implementations in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language search query describing what code you're looking for",
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Current project identifier",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Max number of snippets to return",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["query", "project_id", "k"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    {
        "type": "function",
        "function": {
            "name": "explain_code",
            "description": "Explain the purpose and behavior of a specific code fragment. Use this when the user asks about what a particular function, class, or code section does.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Symbol name (e.g., 'ClassName.method_name') or file path with line number (e.g., 'src/main.py:45')",
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Current project identifier",
                    },
                },
                "required": ["location", "project_id"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    {
        "type": "function",
        "function": {
            "name": "generate_tests",
            "description": "Generate comprehensive unit tests for a specific function or class. Use this when the user requests test creation or wants to improve test coverage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Name of the function or class to generate tests for (e.g., 'UserService.authenticate')",
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Current project identifier",
                    },
                },
                "required": ["symbol", "project_id"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    {
        "type": "function",
        "function": {
            "name": "similar_code",
            "description": "Find code snippets that are semantically similar to a reference code chunk. Use this to identify patterns, duplicated logic, or related implementations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chunk_id": {
                        "type": "integer",
                        "description": "Reference chunk identifier to find similar code for",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of similar chunks to return",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": ["chunk_id", "k"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    {
        "type": "function",
        "function": {
            "name": "search_commits",
            "description": "Search commit messages and history for information about code changes, bug fixes, or feature implementations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term for commit messages (e.g., 'fix authentication', 'add feature')",
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Current project identifier",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of commits to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query", "project_id"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    {
        "type": "function",
        "function": {
            "name": "git_blame",
            "description": "Get blame information for a specific file and line to see who last modified code and when.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to blame",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "Specific line number to get blame for",
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Current project identifier",
                    },
                },
                "required": ["file_path", "project_id"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_code_quality",
            "description": "Run static analysis on code to identify potential issues, style violations, or improvements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file or directory to analyze",
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Current project identifier",
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "Type of analysis to run",
                        "enum": ["linting", "security", "complexity", "all"],
                        "default": "linting"
                    },
                },
                "required": ["file_path", "project_id"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_documentation",
            "description": "Fetch and analyze documentation from web URLs or API endpoints. Use this when you need current information about libraries, frameworks, APIs, or technologies that might not be in your training data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch documentation from (e.g., official API docs, GitHub README, documentation sites)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Specific query or topic to focus on when analyzing the documentation",
                    },
                    "format": {
                        "type": "string",
                        "description": "Expected format of the documentation",
                        "enum": ["markdown", "html", "json", "text", "auto"],
                        "default": "auto"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "Maximum content length to process (in characters)",
                        "default": 50000,
                        "minimum": 1000,
                        "maximum": 200000
                    }
                },
                "required": ["url", "query"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    },
    {
        "type": "function", 
        "function": {
            "name": "comprehensive_analysis",
            "description": "Perform deep, multi-step analysis of code, documentation, or complex problems using structured thinking approaches. This tool enables Chain-of-Thought, Tree-of-Thought, and reflection-based reasoning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The complex task or problem to analyze",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context, code snippets, or relevant information",
                    },
                    "thinking_mode": {
                        "type": "string",
                        "description": "Type of comprehensive thinking to apply",
                        "enum": ["chain_of_thought", "tree_of_thought", "reflection", "step_by_step", "pros_cons", "root_cause"],
                        "default": "chain_of_thought"
                    },
                    "depth": {
                        "type": "string",
                        "description": "Depth of analysis required",
                        "enum": ["surface", "detailed", "comprehensive", "exhaustive"],
                        "default": "detailed"
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Current project identifier for context",
                    }
                },
                "required": ["task", "project_id"],
                "additionalProperties": False,
            },
        },
        "strict": True,
    }
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _extract_llm_response_content(response: Any) -> str:
    """Extract text content from LLM response (both Chat Completions and Responses API)."""
    # Azure Responses API format
    if hasattr(response, "output") and response.output:
        for item in response.output:
            if hasattr(item, "content") and item.content:
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
    if hasattr(response, "choices") and response.choices:
        return response.choices[0].message.content or ""

    # Legacy format
    if hasattr(response, "output_text"):
        return response.output_text or ""

    # Fallback
    return str(response)


async def _tool_file_search(
    args: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    query: str = args["query"]
    project_id: int = int(args["project_id"])
    k: int = int(args.get("k", 5))

    ctx_builder = ContextBuilder(db)  # type: ignore[arg-type]
    ctx = await ctx_builder.extract_context(query, project_id)
    chunks = ctx.get("chunks", [])[:k]
    return {"chunks": chunks}


async def _tool_explain_code(
    args: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    location: str = args["location"].strip()
    project_id: int = int(args["project_id"])

    # Re-use existing ExplainCommand logic to build the prompt, then call LLM.
    cmd = ExplainCommand()
    cmd_result = await cmd.execute(
        location, {"project_id": project_id, "chunks": []}, db
    )

    if not cmd_result.get("success"):
        return {"error": cmd_result.get("message", "Unable to generate explanation")}

    prompt = cmd_result["prompt"]
    response = await llm_client.complete(
        messages=[{"role": "user", "content": prompt}], stream=False
    )

    explanation = _extract_llm_response_content(response)
    return {"explanation": explanation}


async def _tool_generate_tests(
    args: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    symbol: str = args["symbol"].strip()
    project_id: int = int(args["project_id"])

    cmd = GenerateTestsCommand()
    cmd_result = await cmd.execute(symbol, {"project_id": project_id, "chunks": []}, db)

    if not cmd_result.get("success"):
        return {"error": cmd_result.get("message", "Unable to create tests")}

    prompt = cmd_result["prompt"]
    response = await llm_client.complete(
        messages=[{"role": "user", "content": prompt}], stream=False
    )

    tests = _extract_llm_response_content(response)
    return {"tests": tests}


async def _tool_similar_code(
    args: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    from app.models.code import (
        CodeEmbedding,
        CodeDocument,
    )  # local import to avoid circular
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


async def _tool_search_commits(
    args: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    """Search commit history for a project."""
    from app.models.project import Project
    from app.services.git_history_searcher import GitHistorySearcher
    
    query: str = args["query"]
    project_id: int = int(args["project_id"])
    limit: int = int(args.get("limit", 10))
    
    try:
        # Get project to find repository path
        if isinstance(db, AsyncSession):
            from sqlalchemy import select
            project_stmt = select(Project).where(Project.id == project_id)
            result = await db.execute(project_stmt)
            project = result.scalar_one_or_none()
        else:
            project = db.query(Project).filter_by(id=project_id).first()
            
        if not project:
            return {"error": "Project not found"}
            
        # Construct repository path - this would typically be stored in project metadata
        repo_path = f"repos/project_{project_id}"
        
        git_searcher = GitHistorySearcher(repo_path)
        commits = git_searcher.search_commits(query, limit)
        
        return {"commits": commits}
        
    except Exception as e:
        logger.error(f"Commit search failed: {e}")
        return {"error": f"Failed to search commits: {str(e)}"}


async def _tool_git_blame(
    args: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    """Get git blame information for a file and line."""
    from app.models.project import Project
    from app.services.git_history_searcher import GitHistorySearcher
    
    file_path: str = args["file_path"]
    project_id: int = int(args["project_id"])
    line_number: int = args.get("line_number")
    
    try:
        # Get project to find repository path
        if isinstance(db, AsyncSession):
            from sqlalchemy import select
            project_stmt = select(Project).where(Project.id == project_id)
            result = await db.execute(project_stmt)
            project = result.scalar_one_or_none()
        else:
            project = db.query(Project).filter_by(id=project_id).first()
            
        if not project:
            return {"error": "Project not found"}
            
        repo_path = f"repos/project_{project_id}"
        
        git_searcher = GitHistorySearcher(repo_path)
        
        if line_number:
            blame_info = git_searcher.get_blame(file_path, line_number)
        else:
            # Get blame for entire file (first 50 lines)
            blame_info = git_searcher.get_blame(file_path, 1, context_lines=50)
            
        return {"blame": blame_info}
        
    except Exception as e:
        logger.error(f"Git blame failed: {e}")
        return {"error": f"Failed to get blame information: {str(e)}"}


async def _tool_analyze_code_quality(
    args: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    """Run static analysis on code."""
    from app.models.project import Project
    from app.services.static_analysis_searcher import StaticAnalysisSearcher
    
    file_path: str = args["file_path"]
    project_id: int = int(args["project_id"])
    analysis_type: str = args.get("analysis_type", "linting")
    
    try:
        # Get project to find repository path
        if isinstance(db, AsyncSession):
            from sqlalchemy import select
            project_stmt = select(Project).where(Project.id == project_id)
            result = await db.execute(project_stmt)
            project = result.scalar_one_or_none()
        else:
            project = db.query(Project).filter_by(id=project_id).first()
            
        if not project:
            return {"error": "Project not found"}
            
        repo_path = f"repos/project_{project_id}"
        
        analyzer = StaticAnalysisSearcher(repo_path)
        
        if analysis_type == "linting":
            results = analyzer.run_pylint(file_path)
        elif analysis_type == "security":
            results = analyzer.run_security_analysis(file_path)
        elif analysis_type == "complexity":
            results = analyzer.analyze_complexity(file_path)
        elif analysis_type == "all":
            # Run all analysis types
            lint_results = analyzer.run_pylint(file_path)
            security_results = analyzer.run_security_analysis(file_path)
            complexity_results = analyzer.analyze_complexity(file_path)
            
            results = {
                "linting": lint_results,
                "security": security_results,
                "complexity": complexity_results
            }
        else:
            return {"error": f"Unknown analysis type: {analysis_type}"}
            
        return {"analysis": results}
        
    except Exception as e:
        logger.error(f"Code analysis failed: {e}")
        return {"error": f"Failed to analyze code: {str(e)}"}


async def _tool_fetch_documentation(
    args: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    """Fetch and analyze documentation from web URLs."""
    import aiohttp
    import asyncio
    from urllib.parse import urlparse
    from bs4 import BeautifulSoup
    import markdownify
    
    url: str = args["url"]
    query: str = args["query"]
    format_type: str = args.get("format", "auto")
    max_length: int = int(args.get("max_length", 50000))
    
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {"error": "Invalid URL provided"}
        
        # Fetch content with timeout
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AI Documentation Fetcher)"
        }
        
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"error": f"HTTP {response.status}: Unable to fetch documentation"}
                
                content_type = response.headers.get("content-type", "").lower()
                raw_content = await response.text()
        
        # Process content based on format
        processed_content = ""
        
        if format_type == "auto":
            # Auto-detect format based on content type and URL
            if "application/json" in content_type:
                format_type = "json"
            elif "text/markdown" in content_type or url.endswith(".md"):
                format_type = "markdown"
            elif "text/html" in content_type or "html" in content_type:
                format_type = "html"
            else:
                format_type = "text"
        
        if format_type == "html":
            # Parse HTML and convert to markdown for better processing
            soup = BeautifulSoup(raw_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Convert to markdown
            processed_content = markdownify.markdownify(str(soup), heading_style="ATX")
            
        elif format_type == "json":
            # Pretty format JSON for analysis
            import json
            try:
                json_data = json.loads(raw_content)
                processed_content = json.dumps(json_data, indent=2)
            except json.JSONDecodeError:
                processed_content = raw_content
                
        elif format_type == "markdown":
            processed_content = raw_content
            
        else:  # text
            processed_content = raw_content
        
        # Truncate if too long
        if len(processed_content) > max_length:
            processed_content = processed_content[:max_length] + "\n\n[Content truncated...]"
        
        # Use LLM to analyze the documentation based on the query
        analysis_prompt = f"""Analyze the following documentation and answer this specific query: {query}

Documentation from {url}:
---
{processed_content}
---

Please provide a comprehensive analysis focusing on the query. Extract relevant information, code examples, configuration details, and any important notes or warnings."""

        response = await llm_client.complete(
            messages=[{"role": "user", "content": analysis_prompt}], 
            stream=False
        )
        
        analysis = _extract_llm_response_content(response)
        
        return {
            "url": url,
            "query": query,
            "content_length": len(processed_content),
            "format": format_type,
            "analysis": analysis,
            "raw_content": processed_content[:2000] + "..." if len(processed_content) > 2000 else processed_content
        }
        
    except asyncio.TimeoutError:
        return {"error": "Request timed out while fetching documentation"}
    except Exception as e:
        logger.error(f"Documentation fetch failed: {e}")
        return {"error": f"Failed to fetch documentation: {str(e)}"}


async def _tool_comprehensive_analysis(
    args: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    """Perform comprehensive analysis using structured thinking approaches."""
    
    task: str = args["task"]
    context: str = args.get("context", "")
    thinking_mode: str = args.get("thinking_mode", "chain_of_thought")
    depth: str = args.get("depth", "detailed")
    project_id: int = int(args["project_id"])
    
    try:
        # Build comprehensive analysis prompt based on thinking mode
        if thinking_mode == "chain_of_thought":
            thinking_prompt = f"""Let's approach this step by step using Chain of Thought reasoning:

Task: {task}

Context: {context}

Please work through this systematically:
1. First, let me understand what is being asked
2. Then identify the key components and relationships
3. Analyze each component carefully
4. Consider implications and dependencies
5. Synthesize findings into a comprehensive solution

Let me think through each step:"""

        elif thinking_mode == "tree_of_thought":
            thinking_prompt = f"""Let's explore this using Tree of Thought reasoning, considering multiple paths:

Task: {task}
Context: {context}

I'll explore different approaches and evaluate them:

Branch 1: [Direct approach]
Branch 2: [Alternative approach] 
Branch 3: [Creative approach]

For each branch, I'll evaluate:
- Feasibility
- Pros and cons
- Potential outcomes
- Resource requirements

Then select the best path forward:"""

        elif thinking_mode == "reflection":
            thinking_prompt = f"""Let me analyze this using reflective reasoning:

Task: {task}
Context: {context}

Initial thoughts:
[First assessment]

Let me step back and reconsider:
- What assumptions am I making?
- What might I be missing?
- Are there alternative perspectives?
- What could go wrong?

Revised analysis:
[Updated understanding]

Final reflection:
[Comprehensive conclusion]"""

        elif thinking_mode == "step_by_step":
            thinking_prompt = f"""I'll break this down into clear, sequential steps:

Task: {task}
Context: {context}

Step 1: Problem Definition
Step 2: Requirements Analysis  
Step 3: Solution Design
Step 4: Implementation Planning
Step 5: Risk Assessment
Step 6: Testing Strategy
Step 7: Final Recommendations

Let me work through each step methodically:"""

        elif thinking_mode == "pros_cons":
            thinking_prompt = f"""Let me analyze this using pros and cons methodology:

Task: {task}
Context: {context}

Pros (Benefits/Advantages):
- 
-
-

Cons (Drawbacks/Challenges):
-
-
-

Neutral Considerations:
-
-

Risk Assessment:
-
-

Final Recommendation:
Based on this analysis:"""

        elif thinking_mode == "root_cause":
            thinking_prompt = f"""Let me perform root cause analysis:

Task: {task}
Context: {context}

What is the core problem we're trying to solve?

Why does this problem exist?
- Level 1: Immediate causes
- Level 2: Underlying factors  
- Level 3: Root causes

What are the contributing factors?

What would happen if we don't address this?

What are the most effective intervention points?

Comprehensive solution addressing root causes:"""

        # Adjust detail level based on depth parameter
        if depth == "surface":
            thinking_prompt += "\n\nProvide a concise analysis focusing on key points."
        elif depth == "comprehensive": 
            thinking_prompt += "\n\nProvide an in-depth analysis covering all aspects, edge cases, and implications."
        elif depth == "exhaustive":
            thinking_prompt += "\n\nProvide an exhaustive analysis covering every possible angle, alternative, and consideration."
        
        # Get relevant project context if available
        if project_id:
            ctx_builder = ContextBuilder(db)  # type: ignore[arg-type]
            project_context = await ctx_builder.extract_context(task, project_id)
            if project_context.get("chunks"):
                context_summary = "\n".join([
                    f"File: {chunk.get('file_path', 'unknown')}\n{chunk.get('content', '')[:500]}..."
                    for chunk in project_context["chunks"][:3]
                ])
                thinking_prompt += f"\n\nRelevant project context:\n{context_summary}"
        
        # Execute the analysis with appropriate thinking configuration
        if settings.claude_extended_thinking and settings.claude_thinking_mode != "off":
            # Use Claude's extended thinking for this analysis
            response = await llm_client.complete(
                messages=[{"role": "user", "content": thinking_prompt}],
                stream=False
            )
        else:
            # Use regular completion
            response = await llm_client.complete(
                messages=[{"role": "user", "content": thinking_prompt}], 
                stream=False
            )
        
        analysis_result = _extract_llm_response_content(response)
        
        return {
            "task": task,
            "thinking_mode": thinking_mode,
            "depth": depth,
            "analysis": analysis_result,
            "context_used": bool(context),
            "project_context_available": bool(project_id and project_context.get("chunks")) if project_id else False
        }
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}")
        return {"error": f"Failed to perform analysis: {str(e)}"}


_HANDLERS: Dict[str, Callable[[Dict[str, Any], Session | AsyncSession], Any]] = {
    "file_search": _tool_file_search,
    "explain_code": _tool_explain_code,
    "generate_tests": _tool_generate_tests,
    "similar_code": _tool_similar_code,
    "search_commits": _tool_search_commits,
    "git_blame": _tool_git_blame,
    "analyze_code_quality": _tool_analyze_code_quality,
    "fetch_documentation": _tool_fetch_documentation,
    "comprehensive_analysis": _tool_comprehensive_analysis,
}


async def call_tool(
    name: str, arguments: Dict[str, Any], db: Session | AsyncSession
) -> Dict[str, Any]:
    """Execute *name* tool with *arguments* and return result.

    Follows OpenAI Responses API function calling patterns:
    - Validates arguments against function schema
    - Returns properly formatted results
    - Handles errors gracefully with structured responses
    """

    handler = _HANDLERS.get(name)
    if not handler:
        logger.warning("Unknown tool requested: %s", name)
        return {
            "success": False,
            "error": f"Tool '{name}' not available",
            "error_type": "tool_not_found",
        }

    # Validate arguments against schema if available
    validation_error = _validate_tool_arguments(name, arguments)
    if validation_error:
        return {
            "success": False,
            "error": validation_error,
            "error_type": "invalid_arguments",
        }

    try:
        result = await handler(arguments, db)

        # Ensure result is properly formatted
        if isinstance(result, dict) and "error" in result:
            # Handler returned an error
            return {
                "success": False,
                "error": result["error"],
                "error_type": "execution_error",
            }
        else:
            # Success case
            return {"success": True, "data": result}

    except Exception as exc:  # noqa: BLE001
        logger.error("Tool '%s' failed: %s", name, exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "error_type": "execution_exception",
        }


def _validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> str | None:
    """Validate tool arguments against schema.

    Returns error message if validation fails, None if valid.
    """
    # Find the tool schema
    tool_schema = None
    for schema in TOOL_SCHEMAS:
        if schema["function"]["name"] == tool_name:
            tool_schema = schema
            break

    if not tool_schema:
        return None  # No schema to validate against

    params_schema = tool_schema["function"].get("parameters", {})
    required_fields = params_schema.get("required", [])
    properties = params_schema.get("properties", {})

    # Check required fields
    for field in required_fields:
        if field not in arguments:
            return f"Missing required parameter: {field}"

    # Check field types
    for field, value in arguments.items():
        if field in properties:
            expected_type = properties[field].get("type")
            if expected_type == "string" and not isinstance(value, str):
                return f"Parameter '{field}' must be a string"
            elif expected_type == "integer" and not isinstance(value, int):
                return f"Parameter '{field}' must be an integer"
            elif expected_type == "number" and not isinstance(value, (int, float)):
                return f"Parameter '{field}' must be a number"

    return None  # Validation passed


def format_tool_result_for_api(result: Dict[str, Any]) -> str:
    """Format tool result for inclusion in API response.

    Follows OpenAI function calling documentation:
    - Results must be strings
    - Can be JSON, plain text, or error messages
    - Should indicate success/failure clearly
    """
    import json

    if result.get("success"):
        # Success case - return the data
        data = result.get("data", {})
        if isinstance(data, str):
            return data
        else:
            return json.dumps(data)
    else:
        # Error case - return structured error
        error_response = {
            "error": result.get("error", "Unknown error"),
            "error_type": result.get("error_type", "unknown"),
        }
        return json.dumps(error_response)
