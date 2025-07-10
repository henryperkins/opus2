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


# ---------------------------------------------------------------------------
# OpenAI-compatible response helpers ----------------------------------------
# ---------------------------------------------------------------------------
#
# A growing number of provider implementations (pure OpenAI, Azure OpenAI
# *Chat Completions* variant, third-party wrappers) share the **exact same**
# logic for extracting text content, tool call metadata and for formatting
# tool call *results* according to the canonical OpenAI schema.  Instead of
# duplicating those small but non-trivial snippets across every class we
# expose them as stand-alone helpers.  Providers that work with the OpenAI
# JSON structure can now `import` and delegate to the functions below which
# keeps their own code minimal and avoids inevitable divergence over time.




def extract_content_openai(response: Any) -> str:  # noqa: D401 – simple description
    """Return *response* content for OpenAI-style objects.

    The SDK returns a *choices* list whose first element contains the
    assistant message.  When the message is still streaming the *content*
    attribute may be *None* – callers of this helper typically check for an
    empty string in that situation.
    """

    if hasattr(response, "choices") and response.choices:
        return response.choices[0].message.content or ""
    return ""


def extract_tool_calls_openai(response: Any):
    """Extract tool call metadata from an OpenAI-style *response*."""

    tool_calls: list[dict[str, Any]] = []

    if hasattr(response, "choices") and response.choices:
        message = response.choices[0].message
        if hasattr(message, "tool_calls") and message.tool_calls:
            for call in message.tool_calls:
                tool_calls.append({
                    "id": call.id,
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                })

    return tool_calls


def format_tool_result_openai(tool_call_id: str, tool_name: str, result: str):
    """Return *tool result* message formatted for OpenAI-style providers."""

    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": result,
    }



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
