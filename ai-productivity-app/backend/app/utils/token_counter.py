"""
Unified token counting utilities for the RAG system.

This module provides consistent token counting across the application
to avoid discrepancies between different estimation methods.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global tokenizer instance to avoid repeated initialization
_tokenizer = None
_fallback_mode = False


def get_tokenizer(model_name: str = "gpt-3.5-turbo"):
    """Get tiktoken tokenizer with fallback handling."""
    global _tokenizer, _fallback_mode
    
    if _tokenizer is not None:
        return _tokenizer, _fallback_mode
    
    try:
        import tiktoken
        try:
            _tokenizer = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to a common encoding if model not found
            _tokenizer = tiktoken.get_encoding("cl100k_base")
        _fallback_mode = False
        logger.info(f"Using tiktoken for token counting with model: {model_name}")
    except ImportError:
        # Create a fallback encoder that mimics tiktoken interface
        class FallbackEncoder:
            def encode(self, text: str) -> list:
                # Use 3.5 chars per token as approximation (conservative estimate)
                return list(range(max(1, len(text) // 3)))
            
            def decode(self, tokens: list) -> str:
                # Not needed for counting, but maintain interface
                return ""
        
        _tokenizer = FallbackEncoder()
        _fallback_mode = True
        logger.warning("tiktoken not available, using fallback token estimation (3.5 chars/token)")
    
    return _tokenizer, _fallback_mode


def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    """
    Count tokens in text using tiktoken or fallback estimation.
    
    Args:
        text: Text to count tokens for
        model_name: Model name for tiktoken (ignored in fallback mode)
    
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    tokenizer, is_fallback = get_tokenizer(model_name)
    
    try:
        return len(tokenizer.encode(text))
    except Exception as e:
        logger.warning(f"Token counting failed: {e}, using character approximation")
        # Ultimate fallback: 3.5 chars per token
        return max(1, len(text) // 3)


def estimate_max_context_tokens(
    text: str, 
    max_context_length: int,
    model_name: str = "gpt-3.5-turbo"
) -> tuple[str, int]:
    """
    Truncate text to fit within token limit and return actual token count.
    
    Args:
        text: Text to potentially truncate
        max_context_length: Maximum allowed tokens
        model_name: Model name for tiktoken
    
    Returns:
        Tuple of (truncated_text, actual_token_count)
    """
    if not text:
        return "", 0
    
    tokenizer, is_fallback = get_tokenizer(model_name)
    
    try:
        tokens = tokenizer.encode(text)
        
        if len(tokens) <= max_context_length:
            return text, len(tokens)
        
        # Truncate tokens and decode back to text
        truncated_tokens = tokens[:max_context_length]
        if is_fallback:
            # In fallback mode, estimate character truncation
            char_limit = max_context_length * 3  # Conservative estimate
            return text[:char_limit], max_context_length
        else:
            truncated_text = tokenizer.decode(truncated_tokens)
            return truncated_text, len(truncated_tokens)
    
    except Exception as e:
        logger.warning(f"Token truncation failed: {e}, using character approximation")
        # Ultimate fallback: estimate character limit
        char_limit = max_context_length * 3
        if len(text) <= char_limit:
            return text, len(text) // 3
        else:
            return text[:char_limit], max_context_length


def validate_token_usage(
    context: str, 
    max_allowed: int,
    model_name: str = "gpt-3.5-turbo"
) -> dict:
    """
    Validate that context doesn't exceed token limits.
    
    Returns:
        Dict with validation results and metrics
    """
    token_count = count_tokens(context, model_name)
    
    return {
        "token_count": token_count,
        "max_allowed": max_allowed,
        "within_limit": token_count <= max_allowed,
        "overflow": max(0, token_count - max_allowed),
        "utilization_pct": round((token_count / max_allowed) * 100, 1) if max_allowed > 0 else 0
    }
