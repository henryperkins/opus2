from typing import Optional, AsyncIterator, Dict, List
import openai
from openai import AsyncOpenAI, AsyncAzureOpenAI
import logging
try:
    from tenacity import retry, stop_after_attempt, wait_exponential  # type: ignore
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
        self.provider = settings.llm_provider  # 'openai' or 'azure'
        self.model = settings.llm_model or 'gpt-4'
        self.client = self._create_client()

    def _create_client(self):
        """Create provider-specific client."""
        if self.provider == 'azure':
            return AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version="2024-02-01",
                azure_endpoint=settings.azure_openai_endpoint
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
        try:
            params = {
                'model': self.model,
                'messages': messages,
                'temperature': temperature,
                'stream': stream
            }

            if max_tokens:
                params['max_tokens'] = max_tokens

            if stream:
                return self._stream_response(
                    await self.client.chat.completions.create(**params)
                )
            else:
                response = await self.client.chat.completions.create(**params)
                return response.choices[0].message.content

        except openai.APIError as e:
            logger.error(f"LLM API error: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM client error: {e}")
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
