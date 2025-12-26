"""Compression utilities for agent conversation history.

This module provides functions for estimating token counts and compressing
conversation history when it exceeds threshold limits.
"""

from __future__ import annotations

import json
from textwrap import dedent
from typing import TYPE_CHECKING

import structlog

from csbot.agents.messages import (
    AgentMessage,
    AgentModelSpecificMessage,
    AgentTextMessage,
)

if TYPE_CHECKING:
    from csbot.agents.protocol import AsyncAgent

logger = structlog.get_logger(__name__)


def estimate_tokens_for_message(message: AgentMessage) -> int:
    """Estimate the token count for a single message.

    Uses a simple character-based heuristic: ~4 characters per token.
    This is approximate but fast, avoiding API calls for token counting.

    Args:
        message: The message to estimate tokens for.

    Returns:
        Estimated token count.
    """
    if isinstance(message, AgentTextMessage):
        return len(message.content) // 4 + 1
    elif isinstance(message, AgentModelSpecificMessage):
        content = message.content
        if isinstance(content, str):
            return len(content) // 4 + 1
        elif isinstance(content, list):
            total = 0
            for block in content:
                if isinstance(block, dict):
                    total += len(json.dumps(block)) // 4 + 1
                else:
                    total += 100  # Default estimate for unknown content
            return total
        else:
            return 100  # Default estimate for unknown content
    return 100


def estimate_tokens_for_history(history: list[AgentMessage]) -> int:
    """Estimate the total token count for a conversation history.

    Args:
        history: List of messages in the conversation.

    Returns:
        Estimated total token count.
    """
    return sum(estimate_tokens_for_message(msg) for msg in history)


def is_context_window_exceeded_exception(exception: Exception) -> bool:
    """Check if an exception indicates the context window was exceeded.

    Args:
        exception: The exception to check.

    Returns:
        True if this is a context window exceeded error.
    """
    error_str = str(exception).lower()
    return any(
        indicator in error_str
        for indicator in [
            "input is too long",
            "context_length_exceeded",
            "maximum context length",
            "prompt is too long",
            "content exceeds",
        ]
    )


async def compress_history(
    history: list[AgentMessage],
    target_tokens: int,
    compression_agent: AsyncAgent,
) -> list[AgentMessage]:
    """Compress conversation history using an LLM summarization.

    This function preserves the first message (original user request) and
    the last few messages (recent context), while summarizing the middle
    portion into a condensed summary.

    Fail-safe: Returns original history if compression fails.

    Args:
        history: The conversation history to compress.
        target_tokens: Target token count after compression.
        compression_agent: Agent to use for generating the summary.

    Returns:
        Compressed history list, or original history if compression fails.
    """
    if len(history) < 4:
        # Not enough messages to compress meaningfully
        return history

    try:
        # Preserve first message (original request) and last 2 messages (recent context)
        first_message = history[0]
        middle_messages = history[1:-2]
        last_messages = history[-2:]

        if len(middle_messages) == 0:
            return history

        # Create a summary of the middle messages
        middle_content = _format_messages_for_summary(middle_messages)

        summary_prompt = dedent(f"""
            Summarize the following conversation history into a concise summary.
            Focus on key actions taken, tool calls made, and their results.
            Keep important technical details but remove redundant information.
            Target length: approximately {target_tokens // 4} words.

            Conversation to summarize:
            {middle_content}

            Provide a clear, factual summary that preserves the essential context.
        """).strip()

        summary = await compression_agent.create_completion(
            model=compression_agent.model,
            system="You are a helpful assistant that creates concise summaries of conversations.",
            messages=[AgentTextMessage(role="user", content=summary_prompt)],
            max_tokens=target_tokens,
        )

        # Create compressed history with summary
        summary_message = AgentModelSpecificMessage(
            role="user",
            content=[
                {
                    "type": "text",
                    "text": f"[CONVERSATION SUMMARY - Previous messages compressed]\n{summary}",
                }
            ],
        )

        compressed_history = [first_message, summary_message, *last_messages]

        logger.info(
            "Compressed conversation history",
            original_messages=len(history),
            compressed_messages=len(compressed_history),
            original_tokens=estimate_tokens_for_history(history),
            compressed_tokens=estimate_tokens_for_history(compressed_history),
        )

        return compressed_history

    except Exception as e:
        logger.warning(
            "Failed to compress history, returning original",
            error=str(e),
            history_length=len(history),
        )
        # Fail-safe: return original history
        return history


def _format_messages_for_summary(messages: list[AgentMessage]) -> str:
    """Format messages into a string for summarization.

    Args:
        messages: Messages to format.

    Returns:
        Formatted string representation.
    """
    formatted_parts: list[str] = []

    for msg in messages:
        role = msg.role.upper()
        if isinstance(msg, AgentTextMessage):
            content = msg.content
        elif isinstance(msg, AgentModelSpecificMessage):
            content = msg.content
            if isinstance(content, list):
                content_parts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type", "unknown")
                        if block_type == "text":
                            content_parts.append(block.get("text", ""))
                        elif block_type == "tool_use":
                            tool_name = block.get("name", "unknown")
                            tool_input = json.dumps(block.get("input", {}))
                            content_parts.append(f"[Tool call: {tool_name}({tool_input})]")
                        elif block_type == "tool_result":
                            tool_content = block.get("content", "")
                            # Truncate long tool results
                            if len(str(tool_content)) > 500:
                                tool_content = str(tool_content)[:500] + "..."
                            content_parts.append(f"[Tool result: {tool_content}]")
                content = "\n".join(content_parts)
            else:
                content = str(content)
        else:
            content = str(msg)

        formatted_parts.append(f"{role}: {content}")

    return "\n\n".join(formatted_parts)
