from typing import Optional, AsyncIterator, Dict, List
import openai
from openai import AsyncOpenAI, AsyncAzureOpenAI
import logging
try:
    from azure.identity import (
        DefaultAzureCredential, 
        get_bearer_token_provider
    )
    HAS_AZURE_IDENTITY = True
except ImportError:
    HAS_AZURE_IDENTITY = False
    DefaultAzureCredential = None
    get_bearer_token_provider = None

try:
    from tenacity import (
        retry, 
        stop_after_attempt, 
        wait_exponential
    )  # type: ignore
except ModuleNotFoundError:  # Fallback for environments without tenacity
    import functools

    def retry(*dargs, **dkwargs):  # noqa: D401 – simple wrapper
        """No-op retry decorator used when tenacity is unavailable."""

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):  # pylint: disable=missing-docstring
                return await func(*args, **kwargs)

            return wrapper

        # If used as @retry without (), dargs[0] is function
        if dargs and callable(dargs[0]):
            return decorator(dargs[0])

        return decorator

    # Dummy stop/ wait for signature compatibility
    def stop_after_attempt(n):  # noqa: D401
        return None

    def wait_exponential(**_):  # noqa: D401
        return None
from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified client for LLM providers."""

    def __init__(self):
        # The *active* model can change at runtime when we need to fall back
        # from a premium model (e.g. gpt-4) to a broadly available one.
        self.provider = settings.llm_provider  # 'openai' or 'azure'
        # Primary model comes from the new *llm_default_model* setting.  This
        # can be overridden via the ``LLM_MODEL`` environment variable.
        self.active_model = settings.llm_default_model

        # Keep reference to a stable fallback so we can retry when the
        # requested model is unavailable.
        self._fallback_model = "gpt-3.5-turbo"

        self.client = self._create_client()

    def _create_client(self):
        """Create provider-specific client."""
        if self.provider == 'azure':
            return AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )
        else:
            return AsyncOpenAI(api_key=settings.openai_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ):
        """Get completion from LLM."""
        # We attempt the call *once* with the currently active model.  If the
        # provider responds with a *model_not_found* error we transparently
        # switch to the fallback model and retry **once**.

        async def _invoke(model_name: str):
            params = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": stream,
            }
            if max_tokens:
                params["max_tokens"] = max_tokens

            if stream:
                raw_stream = await self.client.chat.completions.create(**params)
                return self._stream_response(raw_stream)

            response = await self.client.chat.completions.create(**params)
            return response.choices[0].message.content

        try:
            return await _invoke(self.active_model)

        except Exception as exc:  # pylint: disable=broad-except
            # Detect *model not found* condition – provider libs differ in
            # exact exception classes, therefore we fall back to string
            # inspection which is still deterministic enough.
            error_text = str(exc).lower()
            is_not_found = ("model_not_found" in error_text or
                            "model not found" in error_text or
                            "does not have access to model" in error_text)

            if is_not_found and self.active_model != self._fallback_model:
                logger.warning(
                    "Model '%s' unavailable (reason: %s), falling back to '%s'",
                    self.active_model, str(exc), self._fallback_model
                )
                self.active_model = self._fallback_model
                try:
                    return await _invoke(self.active_model)
                except Exception as second_exc:  # pylint: disable=broad-except
                    logger.error(
                        "Fallback model request failed: %s",
                        second_exc, exc_info=True
                    )
                    raise second_exc from None

            # Non-recoverable or already retried – propagate.
            logger.error("LLM client error: %s", exc, exc_info=True)
            raise

    async def _stream_response(self, stream) -> AsyncIterator[str]:
        """Handle streaming response."""
        try:
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        # Rough estimate: 4 chars per token
        return len(text) // 4

    def prepare_code_context(self, chunks: List[Dict]) -> str:
        """Format code chunks for context."""
        if not chunks:
            return ""

        context_parts = ["Relevant code from the project:\n"]

        for chunk in chunks[:5]:  # Limit to 5 chunks
            context_parts.append(f"""
File: {chunk['file_path']} (lines {chunk['start_line']}-{chunk['end_line']})
Language: {chunk['language']}
{chunk.get('symbol_type', '')} {chunk.get('symbol_name', '')}

```{chunk['language']}
{chunk['content']}
/*
""")

        return '\n'.join(context_parts)


# Global client instance
llm_client = LLMClient()
