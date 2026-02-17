"""Parser for Codex CLI JSONL streaming output.

Codex's --json output uses a two-level type system completely different from
Claude's stream-json format. This module provides a standalone parser that
converts Codex JSONL lines into erk's ExecutorEvent types.

See docs/learned/integrations/codex/codex-jsonl-format.md for format spec.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from erk.core.output_filter import extract_pr_metadata_from_text
from erk_shared.core.prompt_executor import (
    ErrorEvent,
    ExecutorEvent,
    PrNumberEvent,
    PrTitleEvent,
    PrUrlEvent,
    SpinnerUpdateEvent,
    TextEvent,
    ToolEvent,
)

logger = logging.getLogger(__name__)


@dataclass
class CodexParserState:
    """Mutable state accumulated across JSONL lines.

    This is explicitly NOT frozen — it is mutable parsing state passed by
    reference across parse_codex_jsonl_line() calls. This is the standard
    pattern for stateful stream parsing.
    """

    thread_id: str | None = None
    saw_any_items: bool = False
    saw_any_text: bool = False
    _item_commands: dict[str, str] = field(default_factory=dict)


def parse_codex_jsonl_line(
    line: str,
    worktree_path: Path,
    state: CodexParserState,
) -> list[ExecutorEvent]:
    """Parse a single Codex JSONL line and return executor events.

    Args:
        line: A single line from codex exec --json output.
        worktree_path: Worktree path for relativizing file paths.
        state: Mutable parser state accumulated across lines.

    Returns:
        List of ExecutorEvent objects (may be empty for ignored event types).
    """
    stripped = line.strip()
    if not stripped:
        return []

    data = _safe_parse_json(stripped)
    if data is None:
        return []

    event_type = data.get("type")
    if not isinstance(event_type, str):
        return []

    if event_type == "thread.started":
        return _handle_thread_started(data, state)
    if event_type == "item.started":
        return _handle_item_started(data, state)
    if event_type == "item.completed":
        return _handle_item_completed(data, worktree_path, state)
    if event_type == "turn.failed":
        return _handle_turn_failed(data)
    if event_type == "error":
        return _handle_top_level_error(data)

    # turn.started, turn.completed, item.updated — ignored
    return []


def _safe_parse_json(text: str) -> dict | None:
    """Parse JSON text, returning None on failure.

    JSON parsing is one of the few places where exception handling is
    acceptable — there is no LBYL alternative for malformed JSON.
    """
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return None


def _handle_thread_started(
    data: dict,
    state: CodexParserState,
) -> list[ExecutorEvent]:
    """Capture thread_id from thread.started event."""
    thread_id = data.get("thread_id")
    if isinstance(thread_id, str):
        state.thread_id = thread_id
    return []


def _handle_item_started(
    data: dict,
    state: CodexParserState,
) -> list[ExecutorEvent]:
    """Handle item.started events — emit SpinnerUpdateEvent for in-progress items."""
    state.saw_any_items = True
    item = data.get("item")
    if not isinstance(item, dict):
        return []

    item_type = item.get("type")
    item_id = item.get("id")

    if item_type == "command_execution":
        command = item.get("command", "")
        if isinstance(command, str) and isinstance(item_id, str):
            state._item_commands[item_id] = command
        summary = _truncate(command, 60) if isinstance(command, str) else "command"
        return [SpinnerUpdateEvent(status=f"Running: {summary}...")]

    if item_type == "mcp_tool_call":
        tool_name = item.get("tool", "tool")
        server = item.get("server", "")
        label = f"{server}/{tool_name}" if server else str(tool_name)
        return [SpinnerUpdateEvent(status=f"Using {label}...")]

    return []


def _handle_item_completed(
    data: dict,
    worktree_path: Path,
    state: CodexParserState,
) -> list[ExecutorEvent]:
    """Handle item.completed events — emit TextEvent, ToolEvent, or ErrorEvent."""
    state.saw_any_items = True
    item = data.get("item")
    if not isinstance(item, dict):
        return []

    item_type = item.get("type")

    if item_type == "agent_message":
        return _handle_agent_message(item, state)
    if item_type == "command_execution":
        return _handle_command_execution(item, worktree_path, state)
    if item_type == "file_change":
        return _handle_file_change(item, worktree_path)
    if item_type == "mcp_tool_call":
        return _handle_mcp_tool_call(item)
    if item_type == "error":
        message = item.get("message", "Unknown item error")
        return [ErrorEvent(message=str(message))]

    return []


def _handle_agent_message(
    item: dict,
    state: CodexParserState,
) -> list[ExecutorEvent]:
    """Extract text from agent_message and check for PR metadata."""
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        return []

    state.saw_any_text = True
    events: list[ExecutorEvent] = [TextEvent(content=text)]

    # Extract PR metadata from agent text
    metadata = extract_pr_metadata_from_text(text)
    pr_url = metadata.get("pr_url")
    if pr_url is not None:
        events.append(PrUrlEvent(url=str(pr_url)))
    pr_number = metadata.get("pr_number")
    if pr_number is not None:
        events.append(PrNumberEvent(number=int(pr_number)))
    pr_title = metadata.get("pr_title")
    if pr_title is not None:
        events.append(PrTitleEvent(title=str(pr_title)))

    return events


def _handle_command_execution(
    item: dict,
    worktree_path: Path,
    state: CodexParserState,
) -> list[ExecutorEvent]:
    """Summarize completed command execution as ToolEvent."""
    item_id = item.get("id")
    command = item.get("command", "")
    if not isinstance(command, str):
        command = ""

    # Fall back to captured command from item.started if missing
    if not command and isinstance(item_id, str) and item_id in state._item_commands:
        command = state._item_commands[item_id]

    output = item.get("aggregated_output", "")
    if not isinstance(output, str):
        output = ""
    exit_code = item.get("exit_code")

    cmd_display = _truncate(command, 60)
    output_display = _truncate(output.strip(), 100)

    parts = [f"Ran: {cmd_display}"]
    if output_display:
        parts.append(f"  Output: {output_display}")
    if exit_code is not None and exit_code != 0:
        parts.append(f"  Exit code: {exit_code}")

    return [ToolEvent(summary="\n".join(parts))]


def _handle_file_change(
    item: dict,
    worktree_path: Path,
) -> list[ExecutorEvent]:
    """Summarize file changes as ToolEvent."""
    changes = item.get("changes")
    if not isinstance(changes, list) or not changes:
        return [ToolEvent(summary="File changes applied")]

    summaries: list[str] = []
    for change in changes[:5]:  # Limit to 5 files for brevity
        if not isinstance(change, dict):
            continue
        path = change.get("path", "?")
        kind = change.get("kind", "update")
        # Relativize path if possible
        if isinstance(path, str):
            full_path = worktree_path / path
            if full_path.exists():
                path = str(full_path.relative_to(worktree_path))
        summaries.append(f"  {kind}: {path}")

    remaining = len(changes) - 5
    if remaining > 0:
        summaries.append(f"  ... and {remaining} more")

    return [ToolEvent(summary="File changes:\n" + "\n".join(summaries))]


def _handle_mcp_tool_call(item: dict) -> list[ExecutorEvent]:
    """Summarize MCP tool call completion as ToolEvent."""
    tool = item.get("tool", "unknown")
    server = item.get("server", "")
    status = item.get("status", "")
    error = item.get("error")

    label = f"{server}/{tool}" if server else str(tool)

    if error is not None and isinstance(error, str) and error.strip():
        return [ToolEvent(summary=f"MCP {label}: error - {_truncate(error, 80)}")]

    return [ToolEvent(summary=f"MCP {label}: {status}")]


def _handle_turn_failed(data: dict) -> list[ExecutorEvent]:
    """Extract error from turn.failed event."""
    error = data.get("error", {})
    if isinstance(error, dict):
        message = error.get("message", "Turn failed (no message)")
    else:
        message = "Turn failed (no message)"
    return [ErrorEvent(message=str(message))]


def _handle_top_level_error(data: dict) -> list[ExecutorEvent]:
    """Extract error from top-level error event."""
    message = data.get("message", "Unknown error")
    return [ErrorEvent(message=str(message))]


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
