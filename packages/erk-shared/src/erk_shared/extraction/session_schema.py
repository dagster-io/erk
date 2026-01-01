"""Low-level session entry parsing utilities.

This module provides helper functions that understand the Claude Code session
log entry schema. These are building blocks for higher-level extraction functions.

Session Entry Structure:
    {
        "type": "user|assistant|tool_result|file-history-snapshot",
        "sessionId": "...",
        "timestamp": float|ISO_string,
        "message": {
            "content": [
                {"type": "text", "text": "..."},
                {"type": "tool_use", "id": "...", "name": "...", "input": {...}},
                {"type": "tool_result", "tool_use_id": "..."}
            ]
        },
        "toolUseResult": {
            "agentId": "..."
        }
    }
"""

from typing import Any


def extract_tool_use_id_from_content(content: list[Any]) -> str | None:
    """Extract tool_use_id from message content blocks.

    Searches for tool_result blocks and returns the first tool_use_id found.

    Args:
        content: List of content blocks from a message.

    Returns:
        The tool_use_id if found, None otherwise.
    """
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "tool_result":
            continue
        tool_use_id = block.get("tool_use_id")
        if tool_use_id:
            return tool_use_id
    return None


def extract_task_tool_use_id(
    entry: dict[str, Any],
    subagent_type: str,
) -> str | None:
    """Extract tool_use_id from a Task tool_use with specific subagent_type.

    Searches assistant entry content for Task tool_use blocks where
    subagent_type matches the given value and returns the tool_use_id.

    Args:
        entry: A session log entry of type "assistant".
        subagent_type: The subagent_type to match (e.g., "Plan", "devrun").

    Returns:
        The tool_use_id if found, None otherwise.
    """
    message = entry.get("message", {})
    content = message.get("content", [])
    if not isinstance(content, list):
        return None
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "tool_use":
            continue
        if block.get("name") != "Task":
            continue
        tool_input = block.get("input", {})
        if tool_input.get("subagent_type") != subagent_type:
            continue
        tool_use_id = block.get("id")
        if tool_use_id:
            return tool_use_id
    return None


def extract_agent_id_from_tool_result(
    entry: dict[str, Any],
) -> tuple[str, str] | None:
    """Extract agent_id and tool_use_id from a user entry with toolUseResult.

    Args:
        entry: A session log entry of type "user".

    Returns:
        Tuple of (tool_use_id, agent_id) if found, None otherwise.
    """
    tool_use_result = entry.get("toolUseResult")
    if not isinstance(tool_use_result, dict):
        return None
    agent_id = tool_use_result.get("agentId")
    if not agent_id:
        return None
    message = entry.get("message", {})
    content = message.get("content", [])
    if not isinstance(content, list):
        return None
    tool_use_id = extract_tool_use_id_from_content(content)
    if tool_use_id is None:
        return None
    return (tool_use_id, agent_id)
