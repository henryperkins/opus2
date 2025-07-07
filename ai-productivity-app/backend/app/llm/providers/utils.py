"""Utility functions for LLM providers."""

from typing import Any, Dict, List, Optional


def validate_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert tools to OpenAI format if necessary."""
    validated_tools = []
    for tool in tools:
        if "function" not in tool:
            # Convert to OpenAI format
            validated_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description"),
                        "parameters": tool.get("parameters"),
                    },
                }
            )
        else:
            validated_tools.append(tool)
    return validated_tools


def build_openai_chat_params(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: Optional[int],
    stream: bool,
    tools: Optional[List[Dict[str, Any]]],
    tool_choice: Optional[str | Dict[str, Any]],
    parallel_tool_calls: bool,
    **kwargs,
) -> Dict[str, Any]:
    """Build parameters for OpenAI-compatible chat completion requests."""
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }

    if max_tokens:
        params["max_tokens"] = max_tokens

    if tools:
        params["tools"] = validate_tools(tools)
        if tool_choice:
            params["tool_choice"] = tool_choice
        params["parallel_tool_calls"] = parallel_tool_calls

    params.update(kwargs)
    return {k: v for k, v in params.items() if v is not None}
