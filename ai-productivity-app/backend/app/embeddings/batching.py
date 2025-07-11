# backend/app/embeddings/batching.py
"""Token-aware batching for embedding generation.

This module provides utilities to split text chunks into batches that respect
token limits, preventing oversized batch errors that lead to infinite retry loops.
"""
from __future__ import annotations

import re
from typing import Iterator, List, Protocol

import logging

logger = logging.getLogger(__name__)


class TokenizerProtocol(Protocol):
    """Protocol for tokenizer objects."""

    def encode(self, text: str) -> List[int]:
        """Encode text to tokens."""
        ...


def simple_tokenizer_estimate(text: str) -> int:
    """Simple character-based token estimation (~4 chars per token)."""
    return len(text) // 4


def split_long_text(
    text: str, max_tokens: int, tokenizer_fn=simple_tokenizer_estimate
) -> Iterator[str]:
    """Split a single text into smaller chunks that fit within token limits.

    Args:
        text: The text to split
        max_tokens: Maximum tokens per chunk
        tokenizer_fn: Function to estimate tokens from text

    Yields:
        Text chunks that fit within the token limit
    """
    if tokenizer_fn(text) <= max_tokens:
        yield text
        return

    # Try splitting by paragraphs first
    paragraphs = text.split("\n\n")
    if len(paragraphs) > 1:
        current_chunk = ""
        for para in paragraphs:
            # Check if adding this paragraph would exceed the limit
            test_chunk = current_chunk + ("\n\n" + para if current_chunk else para)
            if tokenizer_fn(test_chunk) > max_tokens:
                # Yield current chunk if it has content
                if current_chunk:
                    yield current_chunk
                    current_chunk = ""

                # If the paragraph itself is too long, split it further
                if tokenizer_fn(para) > max_tokens:
                    yield from split_long_text(para, max_tokens, tokenizer_fn)
                else:
                    current_chunk = para
            else:
                current_chunk = test_chunk

        # Yield any remaining content
        if current_chunk:
            yield current_chunk
        return

    # Fallback: split by sentences
    sentences = re.split(r"[.!?]+\s+", text)
    if len(sentences) > 1:
        current_chunk = ""
        for sentence in sentences:
            test_chunk = current_chunk + (" " + sentence if current_chunk else sentence)
            if tokenizer_fn(test_chunk) > max_tokens:
                if current_chunk:
                    yield current_chunk
                    current_chunk = ""

                if tokenizer_fn(sentence) > max_tokens:
                    # Even single sentence is too long, split by words
                    yield from _split_by_words(sentence, max_tokens, tokenizer_fn)
                else:
                    current_chunk = sentence
            else:
                current_chunk = test_chunk

        if current_chunk:
            yield current_chunk
        return

    # Final fallback: split by words
    yield from _split_by_words(text, max_tokens, tokenizer_fn)


def _split_by_words(
    text: str, max_tokens: int, tokenizer_fn=simple_tokenizer_estimate
) -> Iterator[str]:
    """Split text by words as a last resort."""
    words = text.split()
    current_chunk = ""

    for word in words:
        test_chunk = current_chunk + (" " + word if current_chunk else word)
        if tokenizer_fn(test_chunk) > max_tokens:
            if current_chunk:
                yield current_chunk
                current_chunk = ""

            # If even a single word is too long, truncate it
            if tokenizer_fn(word) > max_tokens:
                # Truncate the word to fit
                while tokenizer_fn(word) > max_tokens and len(word) > 10:
                    word = word[: len(word) // 2]
                logger.warning("Truncated oversized word to fit token limit")

            current_chunk = word
        else:
            current_chunk = test_chunk

    if current_chunk:
        yield current_chunk


def iter_token_limited_batches(
    chunks: List[str], tokenizer, limit: int, safety: int = 200
) -> Iterator[List[str]]:
    """Iterate over batches of text chunks that respect token limits.

    Args:
        chunks: List of text chunks to batch
        tokenizer: Tokenizer object or function to estimate tokens
        limit: Maximum tokens per batch
        safety: Safety margin to subtract from limit

    Yields:
        Batches of text chunks that fit within the token limit
    """
    batch: List[str] = []
    tokens = 0
    effective_limit = limit - safety

    # Handle both tokenizer objects and functions
    if hasattr(tokenizer, "encode"):

        def count_tokens(text: str) -> int:
            return len(tokenizer.encode(text))

    else:
        count_tokens = tokenizer

    for text in chunks:
        text_tokens = count_tokens(text)

        # If single text exceeds limit, split it
        if text_tokens > effective_limit:
            logger.warning(
                "Text chunk with %d tokens exceeds limit %d, splitting",
                text_tokens,
                effective_limit,
            )
            for part in split_long_text(text, effective_limit, count_tokens):
                yield [part]
            continue

        # If adding this text would exceed the limit, yield current batch
        if tokens + text_tokens > effective_limit:
            if batch:  # Only yield non-empty batches
                yield batch
                batch = []
                tokens = 0

        batch.append(text)
        tokens += text_tokens

    # Yield any remaining batch
    if batch:
        yield batch


def estimate_total_tokens(
    texts: List[str], tokenizer_fn=simple_tokenizer_estimate
) -> int:
    """Estimate total tokens for a list of texts."""
    return sum(tokenizer_fn(text) for text in texts)
