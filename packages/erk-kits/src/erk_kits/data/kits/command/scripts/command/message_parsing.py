"""Pure message parsing functions for Claude CLI JSONL output.

These functions transform message dictionaries into structured data
without side effects. They can be easily unit tested.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolUse:
    """Extracted tool use information from assistant message."""

    name: str
    input_params: dict


@dataclass(frozen=True)
class ToolResult:
    """Extracted tool result information from user message."""

    content: str | list
    is_error: bool


def extract_text_from_assistant_message(msg: dict) -> list[str]:
    """Extract text content from assistant message.

    Args:
        msg: Assistant message dict from JSONL stream

    Returns:
        List of text strings found in message content.
        Returns empty list if no text items found.
    """
    message = msg.get("message", {})
    content = message.get("content", [])

    texts = []
    for item in content:
        if item.get("type") == "text":
            text = item.get("text", "")
            texts.append(text)

    return texts


def extract_tool_uses_from_assistant_message(msg: dict) -> list[ToolUse]:
    """Extract tool use items from assistant message.

    Args:
        msg: Assistant message dict from JSONL stream

    Returns:
        List of ToolUse objects with name and input parameters.
        Returns empty list if no tool use items found.
    """
    message = msg.get("message", {})
    content = message.get("content", [])

    tool_uses = []
    for item in content:
        if item.get("type") == "tool_use":
            tool_name = item.get("name", "unknown")
            tool_input = item.get("input", {})
            tool_uses.append(ToolUse(name=tool_name, input_params=tool_input))

    return tool_uses


def extract_tool_results_from_user_message(msg: dict) -> list[ToolResult]:
    """Extract tool results from user message.

    Args:
        msg: User message dict from JSONL stream

    Returns:
        List of ToolResult objects with content and error flag.
        Only includes results that have non-None content.
    """
    message = msg.get("message", {})
    content = message.get("content", [])

    results = []
    for item in content:
        if item.get("type") == "tool_result":
            result_content = item.get("content")
            is_error = item.get("is_error", False)
            if result_content is not None:  # Only include if content exists
                results.append(ToolResult(content=result_content, is_error=is_error))

    return results


def build_result_status_string(msg: dict) -> str:
    """Build completion status string from result message.

    Args:
        msg: Result message dict from JSONL stream

    Returns:
        Formatted status string with emoji, cost, and duration.
    """
    is_error = msg.get("is_error", False)
    status = "❌ Error" if is_error else "✅ Success"

    cost = msg.get("total_cost_usd")
    cost_str = f"${cost:.4f}" if cost is not None else "N/A"

    duration_ms = msg.get("duration_ms", 0)

    return f"\n\n{status} - Cost: {cost_str}, Duration: {duration_ms}ms\n"
