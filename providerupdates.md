# LLM Integration Improvements - Prioritized Implementation Plan

## Priority 1: Add Retry Logic to LLM Client (Quick Win, High Impact)
**Impact**: Drastically reduces user-visible errors from transient failures
**Effort**: Low (2-3 hours)
**Dependencies**: None

### Implementation:

```python
# app/llm/client.py - Add at the top with other imports
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Add retry decorator to complete method
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((APITimeoutError, RateLimitError)),
    reraise=True
)
async def complete(self, ...):
    # Existing implementation
```

### Files to modify:
- `app/llm/client.py` - Add retry decorator and imports

## Priority 2: Adopt Partial Function Call Streaming (Major Latency Reduction)
**Impact**: Reduces requests from 2-3 to 1-2, cutting latency by 30-40%
**Effort**: Medium (4-6 hours)
**Dependencies**: None

### Implementation:

```python
# app/chat/processor.py - Modify _respond_with_llm method

async def _respond_with_llm(self, ...):
    # ... existing setup code ...

    # NEW: Single streaming call with tools enabled
    stream = await llm_client.complete(
        messages=messages,
        temperature=cfg.get("temperature"),
        stream=True,  # Enable streaming
        tools=tools_to_use,  # Keep tools enabled
        tool_choice="auto",
        parallel_tool_calls=True,
        max_tokens=cfg.get("max_tokens"),
    )

    # NEW: Handle streaming with partial function calls
    handler = EnhancedStreamingHandler(websocket)
    full_response, tool_calls = await handler.stream_response_with_tools(stream, ai_msg.id)

    # Process any tool calls that came through
    if tool_calls:
        tool_results = await self._run_tool_calls_from_stream(tool_calls)
        messages.extend(tool_results["message_deltas"])

        # Final streaming response after tools
        final_stream = await llm_client.complete(
            messages=messages,
            temperature=cfg.get("temperature"),
            stream=True,
            tools=None,  # No more tools
            max_tokens=cfg.get("max_tokens"),
        )
        full_response = await handler.stream_response(final_stream, ai_msg.id)
```

### New Enhanced Streaming Handler:

```python
# app/llm/streaming.py - Add new class

class EnhancedStreamingHandler(StreamingHandler):
    """Handle streaming with partial function call support."""

    async def stream_response_with_tools(
        self,
        response_generator: AsyncIterator[Any],
        message_id: int
    ) -> tuple[str, list]:
        """Stream response and collect tool calls."""
        self.message_id = message_id
        tool_calls = []
        current_tool_call = None

        async for chunk in response_generator:
            # Handle OpenAI streaming with tool calls
            if hasattr(chunk, "choices") and chunk.choices:
                choice = chunk.choices[0]

                # Check for tool calls in the delta
                if hasattr(choice.delta, "tool_calls") and choice.delta.tool_calls:
                    for tool_call_delta in choice.delta.tool_calls:
                        if tool_call_delta.index == 0 and tool_call_delta.id:
                            # New tool call starting
                            if current_tool_call:
                                tool_calls.append(current_tool_call)
                            current_tool_call = {
                                "id": tool_call_delta.id,
                                "name": tool_call_delta.function.name,
                                "arguments": ""
                            }
                        if current_tool_call and tool_call_delta.function.arguments:
                            current_tool_call["arguments"] += tool_call_delta.function.arguments

                # Regular content streaming
                elif hasattr(choice.delta, "content") and choice.delta.content:
                    self.buffer.append(choice.delta.content)
                    await self.websocket.send_json({
                        'type': 'ai_stream',
                        'message_id': message_id,
                        'content': choice.delta.content,
                        'done': False
                    })

        # Finalize any pending tool call
        if current_tool_call:
            tool_calls.append(current_tool_call)

        full_content = ''.join(self.buffer)
        return full_content, tool_calls
```

### Files to modify:
- `app/chat/processor.py` - Refactor tool calling flow
- `app/llm/streaming.py` - Add enhanced streaming handler

## Priority 3: Refactor LLMClient with Provider Strategy Pattern (Better Maintainability)
**Impact**: Cleaner code, easier to add new providers
**Effort**: Medium (6-8 hours)
**Dependencies**: None

### Implementation:

```python
# app/llm/providers/base.py - New file

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> Any:
        """Execute completion request."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> AsyncIterator[str]:
        """Execute streaming completion."""
        pass

    @abstractmethod
    def validate_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and format tools for this provider."""
        pass
```

```python
# app/llm/providers/openai.py - New file

class OpenAIProvider(LLMProvider):
    """OpenAI-specific implementation."""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(self, messages, **kwargs):
        clean_kwargs = self._prepare_kwargs(kwargs)
        return await self.client.chat.completions.create(
            messages=messages,
            **clean_kwargs
        )

    async def stream(self, messages, **kwargs):
        clean_kwargs = self._prepare_kwargs(kwargs)
        clean_kwargs['stream'] = True
        response = await self.client.chat.completions.create(
            messages=messages,
            **clean_kwargs
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

```python
# app/llm/client.py - Refactored

class LLMClient:
    """Unified LLM client with provider strategy."""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self._init_providers()
        self.active_provider = None
        self._select_provider()

    def _init_providers(self):
        """Initialize available providers."""
        if settings.openai_api_key:
            self.providers['openai'] = OpenAIProvider(settings.openai_api_key)

        if settings.azure_openai_endpoint:
            self.providers['azure'] = AzureProvider(
                endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key
            )

        if settings.anthropic_api_key:
            self.providers['anthropic'] = AnthropicProvider(settings.anthropic_api_key)

    async def complete(self, messages, **kwargs):
        """Delegate to active provider with retry logic."""
        provider = self._get_active_provider()
        return await self._with_retry(
            provider.complete,
            messages=messages,
            **kwargs
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((APITimeoutError, RateLimitError))
    )
    async def _with_retry(self, func, **kwargs):
        """Execute function with retry logic."""
        return await func(**kwargs)
```

### Files to create/modify:
- Create `app/llm/providers/` directory
- Create `app/llm/providers/base.py`
- Create `app/llm/providers/openai.py`
- Create `app/llm/providers/azure.py`
- Create `app/llm/providers/anthropic.py`
- Refactor `app/llm/client.py`

## Priority 4: Cache Tool Schemas (Quick Performance Win)
**Impact**: Reduces prompt size and token usage
**Effort**: Low (2-3 hours)
**Dependencies**: None

### Implementation:

```python
# app/llm/tools.py - Add caching

from functools import lru_cache
import hashlib

class ToolSchemaCache:
    """Cache tool schemas per provider/model combination."""

    def __init__(self):
        self._cache = {}

    def get_cache_key(self, provider: str, model: str, tools: List[Dict]) -> str:
        """Generate cache key from provider, model, and tool names."""
        tool_names = sorted([t["function"]["name"] for t in tools])
        key_str = f"{provider}:{model}:{','.join(tool_names)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, provider: str, model: str, tools: List[Dict]) -> Optional[str]:
        """Get cached schema reference."""
        key = self.get_cache_key(provider, model, tools)
        return self._cache.get(key)

    def set(self, provider: str, model: str, tools: List[Dict], ref: str):
        """Cache schema reference."""
        key = self.get_cache_key(provider, model, tools)
        self._cache[key] = ref

    @lru_cache(maxsize=32)
    def format_tools_for_provider(self, provider: str, tools_json: str) -> List[Dict]:
        """Format tools for specific provider (cached)."""
        tools = json.loads(tools_json)
        # Provider-specific formatting
        return tools

# Global cache instance
tool_schema_cache = ToolSchemaCache()
```

```python
# app/chat/processor.py - Use cached schemas

async def _respond_with_llm(self, ...):
    # Check cache for tool schema reference
    schema_ref = tool_schema_cache.get(
        llm_client.provider,
        active_model,
        tools_to_use
    )

    if schema_ref:
        # Use reference instead of full schemas
        messages.append({
            "role": "system",
            "content": f"Tools available: {schema_ref}"
        })
        tool_param = None  # Don't send full schemas
    else:
        # First time - send full schemas and cache reference
        tool_param = tools_to_use
        schema_ref = f"tools_{len(tools_to_use)}_{active_model}"
        tool_schema_cache.set(
            llm_client.provider,
            active_model,
            tools_to_use,
            schema_ref
        )
```

### Files to modify:
- `app/llm/tools.py` - Add caching class
- `app/chat/processor.py` - Use cache in tool calling

## Priority 5: Parallelize Tool Execution (Performance Improvement)
**Impact**: Faster tool execution for multiple calls
**Effort**: Low (2-3 hours)
**Dependencies**: None

### Implementation:

```python
# app/chat/processor.py - Modify _run_tool_calls

async def _run_tool_calls(self, response: Any) -> Dict[str, Any]:
    """Execute tool calls in parallel when possible."""
    tool_calls = self._extract_tool_calls(response)

    # Group calls by dependency (assume independent for now)
    async def execute_single_tool(call):
        name = call["name"]
        try:
            args = json.loads(call["arguments"])
        except Exception as exc:
            logger.error("Tool call argument JSON decode failed: %s", exc)
            args = {}

        logger.info("Calling tool %s with %s", name, args)
        try:
            result = await asyncio.wait_for(
                llm_tools.call_tool(name, args, self.db),
                timeout=getattr(settings, "tool_timeout", 30),
            )
            return (call, result)
        except Exception as exc:
            logger.error("Tool '%s' failed: %s", name, exc)
            return (call, {
                "success": False,
                "error": str(exc),
                "error_type": "execution_exception",
            })

    # Execute all tools in parallel
    results = await asyncio.gather(
        *[execute_single_tool(call) for call in tool_calls],
        return_exceptions=False
    )

    # Format results
    deltas = []
    for call, result in results:
        formatted_output = llm_tools.format_tool_result_for_api(result)

        if getattr(llm_client, "use_responses_api", False):
            deltas.append({
                "type": "function_call_output",
                "call_id": call.get("id", "unknown"),
                "output": formatted_output,
            })
        else:
            deltas.append({
                "role": "tool",
                "tool_call_id": call.get("id", "unknown"),
                "name": call["name"],
                "content": formatted_output,
            })

    return {"message_deltas": deltas}
```

### Files to modify:
- `app/chat/processor.py` - Parallelize tool execution

## Priority 6: Add Conversation Summarizer (Token Reduction)
**Impact**: Reduces prompt tokens on long threads by O(n)
**Effort**: High (8-10 hours)
**Dependencies**: None

### Implementation:

```python
# app/services/summarization_service.py - New file

class ConversationSummarizer:
    """Summarize old conversation turns to reduce token usage."""

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.summary_threshold = 15  # Messages before summarizing
        self.summary_cache = {}

    async def should_summarize(
        self,
        session_id: int,
        message_count: int
    ) -> bool:
        """Check if conversation needs summarization."""
        return message_count > self.summary_threshold

    async def create_summary(
        self,
        messages: List[Dict[str, Any]],
        up_to_index: int
    ) -> str:
        """Create summary of messages up to index."""
        # Take first N messages to summarize
        to_summarize = messages[:up_to_index]

        prompt = f"""Summarize this conversation concisely, preserving key context:

{self._format_messages(to_summarize)}

Provide a 2-3 paragraph summary covering:
1. Main topics discussed
2. Key decisions or conclusions
3. Any unresolved questions"""

        response = await self.llm_client.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )

        return self._extract_response_content(response)

    def _format_messages(self, messages: List[Dict]) -> str:
        """Format messages for summarization."""
        lines = []
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content'][:200]}...")
        return "\n\n".join(lines)

    async def get_or_create_summary(
        self,
        session_id: int,
        messages: List[Dict],
        up_to_message_id: int
    ) -> Optional[str]:
        """Get cached summary or create new one."""
        cache_key = f"{session_id}:{up_to_message_id}"

        if cache_key in self.summary_cache:
            return self.summary_cache[cache_key]

        # Find index of message to summarize up to
        up_to_index = None
        for i, msg in enumerate(messages):
            if msg.get("id") == up_to_message_id:
                up_to_index = i
                break

        if up_to_index is None:
            return None

        summary = await self.create_summary(messages, up_to_index)
        self.summary_cache[cache_key] = summary

        return summary
```

```python
# app/chat/context_builder.py - Add summarization support

async def build_conversation_context(
    self,
    session_id: int,
    max_tokens: int,
    use_summary: bool = True
) -> tuple[List[Dict], Optional[str]]:
    """Build conversation context with optional summarization."""

    # Get all messages
    all_messages = await self._get_conversation_messages(session_id)

    if not use_summary or len(all_messages) < 15:
        # No summarization needed
        return self._truncate_to_token_limit(all_messages, max_tokens), None

    # Summarize older messages
    summarizer = ConversationSummarizer(llm_client)
    cutoff_index = len(all_messages) // 2  # Summarize first half

    summary = await summarizer.get_or_create_summary(
        session_id,
        all_messages,
        all_messages[cutoff_index]["id"]
    )

    # Return recent messages + summary
    recent_messages = all_messages[cutoff_index:]
    return self._truncate_to_token_limit(recent_messages, max_tokens), summary
```

### Files to create/modify:
- Create `app/services/summarization_service.py`
- Modify `app/chat/context_builder.py`
- Update `app/chat/processor.py` to use summaries

## Priority 7: Add Response Metrics Tracking (Observability)
**Impact**: Enables cost tracking and optimization
**Effort**: Low (3-4 hours)
**Dependencies**: None

### Implementation:

```python
# app/monitoring/llm_metrics.py - New file

from datetime import datetime
from typing import Dict, Any
import json

class LLMMetricsCollector:
    """Collect and track LLM usage metrics."""

    def __init__(self):
        self.metrics_buffer = []
        self.cost_per_1k_tokens = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            # Add more models
        }

    async def record_completion(
        self,
        provider: str,
        model: str,
        messages: List[Dict],
        response: Any,
        duration_ms: float,
        tool_calls: int = 0
    ):
        """Record metrics for a completion."""
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": provider,
            "model": model,
            "duration_ms": duration_ms,
            "tool_calls": tool_calls,
        }

        # Extract token usage
        if hasattr(response, "usage"):
            metric["prompt_tokens"] = response.usage.prompt_tokens
            metric["completion_tokens"] = response.usage.completion_tokens
            metric["total_tokens"] = response.usage.total_tokens

            # Calculate cost
            if model in self.cost_per_1k_tokens:
                costs = self.cost_per_1k_tokens[model]
                metric["estimated_cost"] = (
                    (metric["prompt_tokens"] / 1000) * costs["input"] +
                    (metric["completion_tokens"] / 1000) * costs["output"]
                )

        self.metrics_buffer.append(metric)

        # Flush to storage if buffer is large
        if len(self.metrics_buffer) > 100:
            await self._flush_metrics()

    async def _flush_metrics(self):
        """Flush metrics to storage."""
        # TODO: Send to monitoring service
        logger.info(f"Flushing {len(self.metrics_buffer)} metrics")
        self.metrics_buffer = []

    def get_session_cost(self, session_id: int) -> float:
        """Calculate total cost for a session."""
        # TODO: Query from storage
        return sum(m.get("estimated_cost", 0) for m in self.metrics_buffer)

# Global metrics collector
llm_metrics = LLMMetricsCollector()
```

```python
# app/llm/client.py - Add metrics hook

async def complete(self, messages, **kwargs):
    """Execute completion with metrics tracking."""
    start_time = time.time()

    try:
        response = await self._execute_completion(messages, **kwargs)

        # Track metrics
        duration_ms = (time.time() - start_time) * 1000
        await llm_metrics.record_completion(
            provider=self.provider,
            model=self.active_model,
            messages=messages,
            response=response,
            duration_ms=duration_ms,
            tool_calls=len(self._extract_tool_calls(response))
        )

        return response
    except Exception as exc:
        # Track failures too
        await llm_metrics.record_failure(
            provider=self.provider,
            model=self.active_model,
            error=str(exc),
            duration_ms=(time.time() - start_time) * 1000
        )
        raise
```

### Files to create/modify:
- Create `app/monitoring/llm_metrics.py`
- Modify `app/llm/client.py` to add hooks
- Create API endpoint for metrics dashboard

## Implementation Timeline

1. **Week 1**: Priorities 1, 4, 5 (Low effort, high impact)
   - Add retry logic
   - Cache tool schemas
   - Parallelize tool execution

2. **Week 2**: Priority 2 (Medium effort, highest impact)
   - Implement partial function call streaming

3. **Week 3**: Priority 3 (Medium effort, maintainability)
   - Refactor to provider strategy pattern

4. **Week 4**: Priorities 6, 7 (Higher effort, long-term benefits)
   - Add conversation summarizer
   - Implement metrics tracking

## Testing Strategy

For each improvement:
1. Unit tests for new components
2. Integration tests with mock providers
3. Load tests to verify performance improvements
4. A/B testing in production with feature flags

## Rollout Strategy

1. Deploy improvements behind feature flags
2. Enable for internal users first
3. Gradual rollout to 10%, 50%, 100% of users
4. Monitor metrics and error rates at each stage
5. Have rollback plan ready
