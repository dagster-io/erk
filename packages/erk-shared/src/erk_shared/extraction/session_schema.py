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

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TaskInfo:
    """Information about a Task tool_use extracted from an assistant entry."""

    tool_use_id: str
    subagent_type: str
    prompt: str


@dataclass(frozen=True)
class AgentInfo:
    """Information about an agent session extracted from Task invocation and result."""

    agent_type: str
    prompt: str
    duration_secs: float | None


def extract_text_from_content_blocks(content: list[Any]) -> str | None:
    """Extract the first text string from a list of content blocks.

    Args:
        content: List of content blocks from a message.

    Returns:
        The first text found, or None if no text block exists.
    """
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            if text:
                return text
        elif isinstance(block, str):
            return block
    return None


def parse_session_timestamp(value: str | float | int | None) -> float | None:
    """Parse a timestamp value to Unix float.

    Handles:
    - None -> None
    - float/int -> returned as float
    - ISO 8601 string (e.g., "2024-12-22T13:20:00.000Z") -> Unix timestamp

    Args:
        value: Timestamp as float, int, ISO string, or None

    Returns:
        Unix timestamp as float, or None if value is None

    Raises:
        TypeError: If value is an unexpected type
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Handle "Z" suffix (UTC)
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        return dt.timestamp()
    msg = f"Unexpected timestamp type: {type(value)}"
    raise TypeError(msg)


def iter_jsonl_entries(content: str) -> Iterator[dict[str, Any]]:
    """Iterate over JSONL content yielding parsed entries.

    Skips blank lines, non-JSON lines, and malformed JSON gracefully.

    Args:
        content: Raw JSONL content as a string.

    Yields:
        Parsed JSON dictionaries for each valid line.
    """
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("{"):
            continue
        # External data parsing - must handle malformed input gracefully
        parsed = _try_parse_json(stripped)
        if parsed is not None:
            yield parsed


def _try_parse_json(text: str) -> dict[str, Any] | None:
    """Try to parse JSON text, returning None on failure.

    This is a boundary function for parsing external/untrusted data.
    Returns None rather than raising to allow graceful iteration over
    potentially malformed JSONL content.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def extract_task_info_from_entry(entry: dict[str, Any]) -> TaskInfo | None:
    """Extract TaskInfo from an assistant entry with a Task tool_use.

    Searches assistant entry content for Task tool_use blocks and extracts
    the tool_use_id, subagent_type, and prompt.

    Args:
        entry: A session log entry of type "assistant".

    Returns:
        TaskInfo if a Task tool_use is found, None otherwise.
    """
    if entry.get("type") != "assistant":
        return None

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

        tool_use_id = block.get("id")
        if not tool_use_id:
            continue

        tool_input = block.get("input", {})
        subagent_type = tool_input.get("subagent_type", "")
        prompt = tool_input.get("prompt", "")

        return TaskInfo(
            tool_use_id=tool_use_id,
            subagent_type=subagent_type,
            prompt=prompt,
        )

    return None


def extract_first_user_message_text(content: str, max_length: int | None) -> str:
    """Extract first user message text from JSONL content (for session summaries).

    Args:
        content: Raw JSONL session content.
        max_length: Maximum length for the result. If None, no truncation is applied.

    Returns:
        First user message text, optionally truncated to max_length.
    """
    for entry in iter_jsonl_entries(content):
        if entry.get("type") != "user":
            continue

        message = entry.get("message", {})
        content_field = message.get("content", "")

        # Content can be string or list of content blocks
        if isinstance(content_field, str):
            text = content_field
        elif isinstance(content_field, list):
            # Find first text block
            extracted = extract_text_from_content_blocks(content_field)
            if extracted is None:
                continue
            text = extracted
        else:
            continue

        # Clean up the text
        text = text.strip()
        if not text:
            continue

        # Truncate with ellipsis if needed
        if max_length is not None and len(text) > max_length:
            return text[: max_length - 3] + "..."
        return text

    return ""


def extract_agent_info_from_jsonl(content: str) -> dict[str, AgentInfo]:
    """Extract agent info from Task tool invocations and their results.

    Uses explicit metadata linking:
    1. Task tool_use entries contain: tool_use.id -> (subagent_type, prompt, timestamp)
    2. tool_result entries contain: tool_use_id + toolUseResult.agentId

    Duration is calculated from entry-level timestamps:
    - tool_use timestamp (when Task was invoked)
    - tool_result timestamp (when Task completed)

    Args:
        content: JSONL content of parent session.

    Returns:
        Dict mapping "agent-<id>" session IDs to AgentInfo.
    """
    # Step 1: Collect Task tool_use entries: tool_use_id -> (type, prompt, timestamp)
    task_info: dict[str, tuple[str, str, float | None]] = {}

    # Step 2: Collect tool_result entries: tool_use_id -> (agentId, timestamp)
    tool_to_agent: dict[str, tuple[str, float | None]] = {}

    for entry in iter_jsonl_entries(content):
        entry_type = entry.get("type")
        message = entry.get("message", {})
        # Timestamp is at root level of entry (may be Unix float or ISO string)
        timestamp = parse_session_timestamp(entry.get("timestamp"))

        if entry_type == "assistant":
            # Look for Task tool_use blocks
            for block in message.get("content", []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") != "Task":
                    continue

                tool_use_id = block.get("id")
                tool_input = block.get("input", {})
                subagent_type = tool_input.get("subagent_type", "")
                prompt = tool_input.get("prompt", "")

                if tool_use_id:
                    task_info[tool_use_id] = (subagent_type, prompt, timestamp)

        elif entry_type == "user":
            # Look for tool_result with toolUseResult.agentId
            tool_use_result = entry.get("toolUseResult")
            if not isinstance(tool_use_result, dict):
                continue
            agent_id = tool_use_result.get("agentId")

            if agent_id:
                # Find the tool_use_id from message content
                for block in message.get("content", []):
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_result":
                        continue
                    tool_use_id = block.get("tool_use_id")
                    if tool_use_id:
                        tool_to_agent[tool_use_id] = (agent_id, timestamp)

    # Step 3: Build final mapping: agent-<id> -> AgentInfo
    agent_infos: dict[str, AgentInfo] = {}
    for tool_use_id, (agent_id, result_timestamp) in tool_to_agent.items():
        info = task_info.get(tool_use_id)
        if info:
            subagent_type, prompt, use_timestamp = info
            # Calculate duration if both timestamps available
            duration_secs: float | None = None
            if use_timestamp is not None and result_timestamp is not None:
                duration_secs = result_timestamp - use_timestamp
            session_id = f"agent-{agent_id}"
            agent_infos[session_id] = AgentInfo(
                agent_type=subagent_type,
                prompt=prompt,
                duration_secs=duration_secs,
            )

    return agent_infos


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


def extract_user_prompts_from_jsonl(
    content: str,
    *,
    max_prompts: int,
    max_prompt_length: int,
) -> list[str]:
    """Extract user prompt text from JSONL session content.

    Iterates through session entries and extracts text from user messages,
    with limits on count and length to keep output manageable.

    Args:
        content: Raw JSONL content as a string.
        max_prompts: Maximum number of prompts to extract.
        max_prompt_length: Maximum length for each prompt (truncated with ...).

    Returns:
        List of user prompt strings, with at most max_prompts items.
    """
    prompts: list[str] = []

    for entry in iter_jsonl_entries(content):
        if entry.get("type") != "user":
            continue

        message = entry.get("message", {})
        content_field = message.get("content", "")

        # Content can be string or list of content blocks
        if isinstance(content_field, str):
            text = content_field
        elif isinstance(content_field, list):
            extracted = extract_text_from_content_blocks(content_field)
            if extracted is None:
                continue
            text = extracted
        else:
            continue

        # Clean up and skip empty
        text = text.strip()
        if not text:
            continue

        # Truncate if needed
        if len(text) > max_prompt_length:
            text = text[: max_prompt_length - 3] + "..."

        prompts.append(text)

        # Stop if we've reached the limit
        if len(prompts) >= max_prompts:
            break

    return prompts
