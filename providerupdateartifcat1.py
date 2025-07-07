# Complete implementation for adding retry logic to LLM client
# This file shows the exact changes needed to app/llm/client.py

# Add these imports at the top of app/llm/client.py (after the existing imports)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)
import time
from datetime import datetime

# Add this custom retry handler after the imports section
def _handle_rate_limit_error(retry_state):
    """Extract Retry-After header from rate limit errors."""
    if retry_state.outcome.failed:
        exc = retry_state.outcome.exception()
        if isinstance(exc, RateLimitError) and hasattr(exc, 'response'):
            retry_after = exc.response.headers.get('Retry-After')
            if retry_after:
                try:
                    return float(retry_after)
                except (ValueError, TypeError):
                    pass
    # Fall back to exponential backoff
    return min(4 * (2 ** (retry_state.attempt_number - 1)), 60)

# Add this decorator to the complete method in LLMClient class
# Replace the existing complete method with this enhanced version:

    @retry(
        stop=stop_after_attempt(settings.llm_max_retries if hasattr(settings, 'llm_max_retries') else 3),
        wait=_handle_rate_limit_error,
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def complete(  # noqa: PLR0913
        self,
        messages: Sequence[Dict[str, Any]] | None = None,
        *,
        input: Sequence[Dict[str, Any]] | str | None = None,
        temperature: float | int | None = None,
        stream: bool = False,
        background: bool = False,
        tools: Any | None = None,
        tool_choice: str | Dict[str, Any] | None = None,
        parallel_tool_calls: bool = True,
        reasoning: Dict[str, Any] | bool | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> Any | AsyncIterator[str]:
        """Wrapper around the underlying Chat Completions / Responses API with automatic retry.

        Automatically retries on:
        - Rate limit errors (respecting Retry-After header)
        - API timeout errors
        - Transient network errors

        Does NOT retry on:
        - Authentication errors
        - Invalid request errors
        - Oversized payload errors
        """

        start_time = time.time()
        request_id = f"req_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{id(self)}"

        try:
            logger.info(
                "LLM request %s started - Provider: %s, Model: %s, Stream: %s",
                request_id, self.provider, model or self.active_model, stream
            )

            # Call the existing implementation (move all the current complete() code here)
            result = await self._complete_internal(
                messages=messages,
                input=input,
                temperature=temperature,
                stream=stream,
                background=background,
                tools=tools,
                tool_choice=tool_choice,
                parallel_tool_calls=parallel_tool_calls,
                reasoning=reasoning,
                max_tokens=max_tokens,
                model=model
            )

            # Log successful completion
            duration = time.time() - start_time
            logger.info(
                "LLM request %s completed successfully in %.2fs",
                request_id, duration
            )

            return result

        except (RateLimitError, APITimeoutError) as exc:
            # These will be retried by tenacity
            logger.warning(
                "LLM request %s failed with retryable error: %s",
                request_id, exc
            )
            raise

        except (AuthenticationError, BadRequestError) as exc:
            # These should NOT be retried
            duration = time.time() - start_time
            logger.error(
                "LLM request %s failed with non-retryable error after %.2fs: %s",
                request_id, duration, exc
            )
            raise

        except RetryError as exc:
            # Max retries exceeded
            duration = time.time() - start_time
            logger.error(
                "LLM request %s failed after %d retries and %.2fs: %s",
                request_id, exc.last_attempt.attempt_number, duration, exc.last_attempt.exception()
            )
            # Re-raise the original exception
            raise exc.last_attempt.exception() from None

        except Exception as exc:
            # Unexpected errors
            duration = time.time() - start_time
            logger.error(
                "LLM request %s failed with unexpected error after %.2fs: %s",
                request_id, duration, exc, exc_info=True
            )
            raise

    async def _complete_internal(
        self,
        messages: Sequence[Dict[str, Any]] | None = None,
        *,
        input: Sequence[Dict[str, Any]] | str | None = None,
        temperature: float | int | None = None,
        stream: bool = False,
        background: bool = False,
        tools: Any | None = None,
        tool_choice: str | Dict[str, Any] | None = None,
        parallel_tool_calls: bool = True,
        reasoning: Dict[str, Any] | bool | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> Any | AsyncIterator[str]:
        """Internal completion method with the existing implementation."""

        # Move ALL the existing complete() method code here
        # This is the exact same code that was in complete(), just moved to this internal method

        if self.client is None:
            raise RuntimeError("LLM client not initialised – missing credentials?")

        # ... rest of the existing complete() implementation ...
        # (Copy all the code from the current complete method here)

# Also add retry logic to generate_response and other public methods:

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        reraise=True
    )
    async def generate_response(self, prompt: str, **kwargs) -> Any:
        """Shortcut for a single-user prompt with automatic retry."""
        messages = [
            {"role": "system", "content": self._DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        return await self.complete(messages, **kwargs)

# Add these configuration settings to app/config.py:
class Settings(BaseSettings):
    # ... existing settings ...

    # LLM retry configuration
    llm_max_retries: int = Field(default=3, description="Maximum retry attempts for LLM calls")
    llm_retry_max_wait: int = Field(default=60, description="Maximum wait time between retries in seconds")
    llm_timeout_seconds: int = Field(default=300, description="Timeout for LLM API calls")

# Add timeout configuration to the client initialization methods:

    def _init_openai_client(self) -> None:
        """Create *AsyncOpenAI* instance with timeout configuration."""
        api_key = os.getenv("OPENAI_API_KEY", settings.openai_api_key)

        if not api_key:
            logger.info("OpenAI API key missing – continuing with stub client")

        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=httpx.Timeout(settings.llm_timeout_seconds, connect=30.0),
            max_retries=0  # We handle retries ourselves with tenacity
        )

    def _init_azure_client(self) -> None:
        """Create *AsyncAzureOpenAI* instance with timeout configuration."""
        # ... existing setup code ...

        extra_kwargs["timeout"] = httpx.Timeout(settings.llm_timeout_seconds, connect=30.0)
        extra_kwargs["max_retries"] = 0  # We handle retries ourselves

        self.client = AsyncAzureOpenAI(**extra_kwargs)

    def _init_anthropic_client(self) -> None:
        """Create *AsyncAnthropic* instance with timeout configuration."""
        # ... existing setup code ...

        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=httpx.Timeout(settings.llm_timeout_seconds, connect=30.0),
            max_retries=0  # We handle retries ourselves
        )
