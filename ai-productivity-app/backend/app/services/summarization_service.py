# backend/app/services/summarization_service.py
"""Intelligent context summarization for overflow content."""

import logging
from typing import List, Dict, Any, Optional
from app.llm.client import llm_client
from app.utils.token_counter import count_tokens

logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for summarizing context when it exceeds token limits."""

    def __init__(self, max_summary_tokens: int = 800):
        self.max_summary_tokens = max_summary_tokens

    async def summarize_overflow_chunks(
        self,
        overflow_chunks: List[Dict[str, Any]],
        query_context: str = "",
        focus_areas: Optional[List[str]] = None,
    ) -> str:
        """Summarize chunks that couldn't fit in the main context window."""

        if not overflow_chunks:
            return ""

        # Prepare content for summarization
        content_parts = []
        for chunk in overflow_chunks:
            metadata = chunk.get("metadata", {})

            # Format each chunk with context
            chunk_text = f"## File: {metadata.get('file_path', 'Unknown')}"
            if metadata.get("symbol_name"):
                chunk_text += f"\n### {metadata.get('symbol_type', 'Symbol')}: {metadata['symbol_name']}"
            if metadata.get("start_line"):
                chunk_text += (
                    f" (lines {metadata['start_line']}-{metadata['end_line']})"
                )

            chunk_text += f"\n\n{chunk['content']}\n"
            content_parts.append(chunk_text)

        combined_content = "\n---\n".join(content_parts)

        # Create focused summarization prompt
        focus_instruction = ""
        if focus_areas:
            focus_instruction = f"\nPay special attention to: {', '.join(focus_areas)}"

        query_instruction = ""
        if query_context:
            query_instruction = f"\nThe user is asking about: {query_context}"

        prompt = f"""Please provide a concise summary of the following code snippets and documentation. Focus on the key functionality, important patterns, and how different components relate to each other.{query_instruction}{focus_instruction}

Keep the summary under {self.max_summary_tokens // 4} words and structure it as:
1. Main components/functions described
2. Key patterns or architectural decisions
3. Important implementation details
4. Relationships between components

Content to summarize:

{combined_content}

Summary:"""

        try:
            response = await llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                max_tokens=self.max_summary_tokens,
            )

            # Extract content from response
            if hasattr(response, "choices") and response.choices:
                summary = response.choices[0].message.content or ""
            elif hasattr(response, "output") and response.output:
                # Handle Azure Responses API format
                summary = ""
                for item in response.output:
                    if hasattr(item, "content"):
                        if isinstance(item.content, str):
                            summary += item.content
                        elif isinstance(item.content, list):
                            for content_item in item.content:
                                if hasattr(content_item, "text"):
                                    summary += content_item.text
            else:
                summary = str(response)

            # Add prefix to indicate this is a summary
            if summary.strip():
                return f"## Summary of Additional Context\n\n{summary.strip()}"
            else:
                return ""

        except Exception as e:
            logger.error(f"Failed to summarize overflow chunks: {e}")
            # Fallback: provide a basic summary
            file_list = [
                chunk.get("metadata", {}).get("file_path", "Unknown")
                for chunk in overflow_chunks
            ]
            unique_files = list(set(file_list))

            return f"## Additional Context Summary\n\nAdditional relevant code found in {len(overflow_chunks)} snippets across {len(unique_files)} files: {', '.join(unique_files[:5])}{'...' if len(unique_files) > 5 else ''}"

    async def summarize_conversation_history(
        self, old_messages: List[Dict[str, Any]], max_summary_length: int = 500
    ) -> str:
        """Summarize old conversation history to maintain context."""

        if not old_messages:
            return ""

        # Format conversation for summarization
        conversation_text = ""
        for msg in old_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "user":
                conversation_text += f"User: {content}\n\n"
            elif role == "assistant":
                # Truncate very long assistant responses for summarization
                truncated_content = (
                    content[:1000] + "..." if len(content) > 1000 else content
                )
                conversation_text += f"Assistant: {truncated_content}\n\n"

        prompt = f"""Please provide a concise summary of this conversation history. Focus on:
1. Key topics discussed
2. Important questions asked by the user
3. Main solutions or information provided
4. Any ongoing context that would be relevant for future questions

Keep the summary under {max_summary_length // 4} words.

Conversation to summarize:

{conversation_text}

Summary:"""

        try:
            response = await llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                stream=False,
                max_tokens=max_summary_length,
            )

            # Extract content (same logic as above)
            if hasattr(response, "choices") and response.choices:
                summary = response.choices[0].message.content or ""
            elif hasattr(response, "output") and response.output:
                summary = ""
                for item in response.output:
                    if hasattr(item, "content"):
                        if isinstance(item.content, str):
                            summary += item.content
            else:
                summary = str(response)

            if summary.strip():
                return f"## Previous Conversation Summary\n\n{summary.strip()}"
            else:
                return ""

        except Exception as e:
            logger.error(f"Failed to summarize conversation history: {e}")
            # Fallback summary
            return f"## Previous Conversation Summary\n\nPrevious discussion covered {len(old_messages)} messages with topics including code analysis and implementation questions."

    def should_summarize_chunks(
        self,
        all_chunks: List[Dict[str, Any]],
        max_context_tokens: int,
        keep_top_n: int = 5,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Determine which chunks to keep vs summarize based on token limits."""

        if len(all_chunks) <= keep_top_n:
            return all_chunks, []

        # Sort chunks by relevance score if available
        sorted_chunks = sorted(
            all_chunks, key=lambda x: x.get("score", 0), reverse=True
        )

        # Keep top chunks that fit in token budget
        kept_chunks = []
        current_tokens = 0

        for chunk in sorted_chunks:
            chunk_tokens = count_tokens(chunk.get("content", ""))

            if (
                current_tokens + chunk_tokens <= max_context_tokens
                and len(kept_chunks) < keep_top_n
            ):
                kept_chunks.append(chunk)
                current_tokens += chunk_tokens
            else:
                break

        # Remaining chunks for summarization
        kept_chunk_ids = {chunk.get("chunk_id") for chunk in kept_chunks}
        overflow_chunks = [
            chunk
            for chunk in sorted_chunks
            if chunk.get("chunk_id") not in kept_chunk_ids
        ]

        return kept_chunks, overflow_chunks

    def should_summarize_conversation(
        self, conversation: List[Dict[str, Any]], max_conversation_tokens: int
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Determine which messages to keep vs summarize."""

        if not conversation:
            return [], []

        # Always keep the last few messages
        keep_recent_count = 6  # Keep last 3 exchanges (user + assistant)

        if len(conversation) <= keep_recent_count:
            return conversation, []

        # Calculate tokens for recent messages
        recent_messages = conversation[-keep_recent_count:]
        recent_tokens = sum(
            count_tokens(msg.get("content", "")) for msg in recent_messages
        )

        if recent_tokens >= max_conversation_tokens:
            # Even recent messages are too long, just keep the last 2
            return conversation[-2:], conversation[:-2]

        # Try to fit more messages within token budget
        kept_messages = recent_messages.copy()
        remaining_tokens = max_conversation_tokens - recent_tokens

        # Go backwards through older messages
        for i in range(len(conversation) - keep_recent_count - 1, -1, -1):
            msg = conversation[i]
            msg_tokens = count_tokens(msg.get("content", ""))

            if msg_tokens <= remaining_tokens:
                kept_messages.insert(0, msg)
                remaining_tokens -= msg_tokens
            else:
                break

        # Messages to summarize
        kept_msg_indices = set(conversation.index(msg) for msg in kept_messages)
        old_messages = [
            msg for i, msg in enumerate(conversation) if i not in kept_msg_indices
        ]

        return kept_messages, old_messages
