import re
import asyncio
from typing import Dict, List, Optional, Callable, Any, Tuple
from sqlalchemy.orm import Session
import logging

from app.models.code import CodeDocument, CodeEmbedding
from app.models.project import Project

# Optional integrations (import guarded to avoid hard dependency during testing)
try:
    from app.services.hybrid_search import HybridSearch  # noqa: F401
except ImportError:  # pragma: no cover
    HybridSearch = None  # type: ignore

try:
    from app.llm.client import LLMClient  # noqa: F401
except ImportError:  # pragma: no cover
    LLMClient = None  # type: ignore

logger = logging.getLogger(__name__)


class SlashCommand:
    """Base class for slash commands."""

    def __init__(self, name: str, description: str, usage: str):
        self.name = name
        self.description = description
        self.usage = usage

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        """Execute command and return result."""
        raise NotImplementedError


class ExplainCommand(SlashCommand):
    """Explain code with context."""

    def __init__(self):
        super().__init__(
            name="explain",
            description="Explain code functionality",
            usage="/explain [file:line] or /explain [symbol]",
        )

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        # Parse arguments
        file_match = re.match(r"(\S+):(\d+)", args)

        if file_match:
            file_path = file_match.group(1)
            line_num = int(file_match.group(2))

            # Get code context
            chunks = context.get("chunks", [])
            relevant_chunk = None

            for chunk in chunks:
                if (
                    chunk["file_path"].endswith(file_path)
                    and chunk["start_line"] <= line_num <= chunk["end_line"]
                ):
                    relevant_chunk = chunk
                    break

            if not relevant_chunk:
                return {
                    "success": False,
                    "message": f"Could not find {file_path}:{line_num}",
                }

            prompt = f"""Explain the following {relevant_chunk['language']} code:

File: {relevant_chunk['file_path']}
Lines {relevant_chunk['start_line']}-{relevant_chunk['end_line']}

{relevant_chunk['content']}

Provide a clear explanation of what this code does, including:
1. Purpose and functionality
2. Input/output behavior
3. Key implementation details
4. Any notable patterns or techniques used"""

        else:
            # Symbol-based explanation
            symbol = args.strip()
            chunks = context.get("chunks", [])

            relevant_chunks = [c for c in chunks if c.get("symbol_name") == symbol]

            if not relevant_chunks:
                return {"success": False, "message": f"Could not find symbol: {symbol}"}

            chunk = relevant_chunks[0]
            prompt = f"""Explain the {chunk['symbol_type']} '{chunk['symbol_name']}':

{chunk['content']}

Provide a comprehensive explanation."""

        return {"success": True, "prompt": prompt, "requires_llm": True}


class GenerateTestsCommand(SlashCommand):
    """Generate unit tests for code."""

    def __init__(self):
        super().__init__(
            name="generate-tests",
            description="Generate unit tests for functions/classes",
            usage="/generate-tests [function_name]",
        )

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        symbol = args.strip()
        chunks = context.get("chunks", [])

        # Find function/class
        relevant_chunks = [
            c
            for c in chunks
            if c.get("symbol_name") == symbol
            and c.get("symbol_type") in ["function", "class", "method"]
        ]

        if not relevant_chunks:
            return {
                "success": False,
                "message": f"Could not find function/class: {symbol}",
            }

        chunk = relevant_chunks[0]
        language = chunk["language"]

        # Language-specific test framework
        framework_map = {
            "python": "pytest",
            "javascript": "Jest",
            "typescript": "Jest with TypeScript",
        }
        framework = framework_map.get(language, "appropriate test framework")

        prompt = f"""Generate comprehensive unit tests for the following {chunk['symbol_type']}:

Language: {language}
File: {chunk['file_path']}

{chunk['content']}

Generate tests using {framework} that cover:
1. Normal operation cases
2. Edge cases
3. Error conditions
4. Any boundary conditions

Include setup/teardown if needed."""

        return {"success": True, "prompt": prompt, "requires_llm": True}


class SummarizePRCommand(SlashCommand):
    """Summarize changes in PR style."""

    def __init__(self):
        super().__init__(
            name="summarize-pr",
            description="Summarize recent changes in PR format",
            usage="/summarize-pr [#commits]",
        )

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        # This would integrate with git in full implementation
        # For now, summarize recent file changes

        project_id = context.get("project_id")

        # Get recent documents
        recent_docs = (
            db.query(CodeDocument)
            .filter_by(project_id=project_id)
            .order_by(CodeDocument.updated_at.desc())
            .limit(10)
            .all()
        )

        if not recent_docs:
            return {"success": False, "message": "No recent changes found"}

        files_summary = []
        for doc in recent_docs:
            files_summary.append(f"- {doc.file_path} ({doc.language})")

        prompt = f"""Create a pull request summary for the following changed files:

{chr(10).join(files_summary)}

Generate a PR description that includes:
1. Summary of changes (bullet points)
2. Type of change (feature/bugfix/refactor)
3. Testing notes
4. Any breaking changes

Format it as a proper GitHub PR description."""

        return {"success": True, "prompt": prompt, "requires_llm": True}


class GrepCommand(SlashCommand):
    """Search codebase for pattern."""

    def __init__(self):
        super().__init__(
            name="grep",
            description="Search code for pattern",
            usage="/grep [pattern] [--type=python]",
        )

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        # Parse arguments
        parts = args.split()
        if not parts:
            return {
                "success": False,
                "message": "Usage: /grep pattern [--type=language]",
            }

        pattern = parts[0]
        language = None

        # Check for type flag
        for part in parts[1:]:
            if part.startswith("--type="):
                language = part.split("=")[1]

        project_id = context.get("project_id")

        # Search in chunks
        query = (
            db.query(CodeEmbedding)
            .join(CodeDocument)
            .filter(
                CodeDocument.project_id == project_id,
                CodeEmbedding.chunk_content.like(f"%{pattern}%"),
            )
        )

        if language:
            query = query.filter(CodeDocument.language == language)

        results = query.limit(10).all()

        if not results:
            return {"success": True, "message": f"No matches found for '{pattern}'"}

        # Format results
        output = [f"Found {len(results)} matches for '{pattern}':\n"]

        for chunk in results:
            # Find matching lines
            lines = chunk.chunk_content.split("\n")
            matches = []

            for i, line in enumerate(lines):
                if pattern.lower() in line.lower():
                    line_num = chunk.start_line + i
                    matches.append(f"{line_num}: {line.strip()}")

            if matches:
                output.append(f"\n{chunk.document.file_path}:")
                output.extend(matches[:3])  # First 3 matches
                if len(matches) > 3:
                    output.append(f"  ... and {len(matches) - 3} more matches")

        return {"success": True, "message": "\n".join(output), "requires_llm": False}


class CommandRegistry:
    """Registry and parser for slash commands."""

    def __init__(self):
        self.commands: Dict[str, SlashCommand] = {}
        self._register_default_commands()

    def _register_default_commands(self):
        """Register built-in commands."""
        self.register(ExplainCommand())
        self.register(GenerateTestsCommand())
        self.register(SummarizePRCommand())
        self.register(GrepCommand())

    def register(self, command: SlashCommand):
        """Register a command."""
        self.commands[command.name] = command

    def parse_message(self, message: str) -> List[Tuple[str, str]]:
        """Extract commands from message."""
        commands = []

        # Match /command args format
        pattern = re.compile(r"/(\w+)\s*([^/]*?)(?=/\w+|$)")

        for match in pattern.finditer(message):
            cmd_name = match.group(1)
            args = match.group(2).strip()

            if cmd_name in self.commands:
                commands.append((cmd_name, args))

        return commands

    async def execute_commands(
        self, message: str, context: Dict, db: Session
    ) -> List[Dict]:
        """Execute all commands in message."""
        commands = self.parse_message(message)
        results = []

        for cmd_name, args in commands:
            command = self.commands.get(cmd_name)
            if command:
                try:
                    result = await command.execute(args, context, db)
                    result["command"] = cmd_name
                    results.append(result)
                except Exception as e:
                    logger.error(f"Command execution failed: {e}")
                    results.append(
                        {
                            "command": cmd_name,
                            "success": False,
                            "message": f"Command failed: {str(e)}",
                        }
                    )

        return results

    def get_suggestions(self, partial: str) -> List[Dict]:
        """Get command suggestions."""
        if not partial.startswith("/"):
            return []

        partial_cmd = partial[1:].lower()
        suggestions = []

        for name, command in self.commands.items():
            if name.startswith(partial_cmd):
                suggestions.append(
                    {
                        "command": name,
                        "description": command.description,
                        "usage": command.usage,
                    }
                )

        # Sort suggestions alphabetically
        suggestions.sort(key=lambda x: x["command"])

        return suggestions


# ---------------------------------------------------------------------------
# Global command registry instance
# ---------------------------------------------------------------------------

# A single shared registry is used across the application so that command
# discovery/execution is consistent everywhere (ChatProcessor, autocompletion
# endpoints, etc.). Importing `command_registry` from this module is therefore
# the canonical way to access registered commands.

command_registry = CommandRegistry()
