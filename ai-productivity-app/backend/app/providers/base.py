import warnings
from typing import Optional, Union

# Assuming GenerationParams and ReasoningParams are defined in a schema file
# from app.schemas.generation import GenerationParams, ReasoningParams

# For now, let's use placeholder classes
class GenerationParams:
    def __init__(self, **kwargs):
        pass

class ReasoningParams:
    def __init__(self, **kwargs):
        pass

class LLMProvider:
    def complete(self, *args, **kwargs):
        """Backward compatibility shim"""
        if len(args) == 6:  # Old signature
            warnings.warn(
                "LLMProvider.complete() old signature is deprecated. "
                "Use complete(messages, model, generation_params, reasoning_params) instead.",
                DeprecationWarning,
                stacklevel=2
            )
            messages, model, temperature, max_tokens, stream, tools = args
            gen_params = GenerationParams(
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                tools=tools
            )
            return self._complete_new(messages, model, gen_params)
        else:
            # New signature
            return self._complete_new(*args, **kwargs)

    def _complete_new(self, messages, model: str,
                     generation_params: GenerationParams,
                     reasoning_params: Optional[ReasoningParams] = None):
        """New implementation"""
        raise NotImplementedError
