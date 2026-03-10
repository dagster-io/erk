"""Parser for GitHub Actions implementation run logs.

Extracts structured summaries from Claude CLI stream-json output embedded
in GitHub Actions log lines. Used by the debug-impl-run exec script.

This module contains only pure parsing functions and frozen dataclasses —
no I/O, no subprocess calls.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from erk.core.output_filter import extract_text_content, summarize_tool_use


@dataclass(frozen=True)
class ToolAction:
    """A single tool invocation extracted from the Claude session."""

    tool_name: str
    summary: str


@dataclass(frozen=True)
class ImplRunSummary:
    """Structured summary of an implementation run session."""

    session_id: str | None
    model: str | None
    duration_ms: int | None
    num_turns: int | None
    is_error: bool | None
    exit_code: int | None
    cost_usd: float | None
    tool_actions: list[ToolAction]
    error_messages: list[str]
    files_read: list[str]
    files_modified: list[str]
    assistant_messages: list[str]


# Regex matching GH Actions timestamp prefix: "2026-01-15T10:30:45.1234567Z "
_GH_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s")


def extract_stream_json_lines(job_log: str) -> list[str]:
    """Extract stream-json lines from a GitHub Actions job log.

    Strips GitHub Actions timestamp prefixes, finds the implementation step
    section (between ``##[group]`` markers containing "Run implementation" or
    "claude" invocations), and returns only the JSON lines.

    Args:
        job_log: Full text of the job log from the GitHub REST API

    Returns:
        List of JSON-line strings (without timestamp prefix)
    """
    lines = job_log.splitlines()
    stripped: list[str] = []
    in_impl_section = False

    for line in lines:
        # Strip GH Actions timestamp prefix
        cleaned = _GH_TIMESTAMP_RE.sub("", line)

        # Detect start of implementation step via group markers
        if cleaned.startswith("##[group]") and _is_impl_step_marker(cleaned):
            in_impl_section = True
            continue

        # Detect end of section
        if in_impl_section and cleaned.startswith("##[endgroup]"):
            in_impl_section = False
            continue

        if not in_impl_section:
            continue

        # Only keep lines that look like JSON
        trimmed = cleaned.strip()
        if trimmed.startswith("{"):
            stripped.append(trimmed)

    # Fallback: if no group markers found, scan all lines for JSON
    if not stripped:
        stripped = _extract_json_lines_from_all(lines)

    return stripped


def _is_impl_step_marker(group_line: str) -> bool:
    """Check if a ##[group] line marks the implementation step."""
    lower = group_line.lower()
    return "run implementation" in lower or "claude" in lower or "plan-implement" in lower


def _extract_json_lines_from_all(lines: list[str]) -> list[str]:
    """Fallback: extract JSON lines from all log lines when no group markers found."""
    result: list[str] = []
    for line in lines:
        cleaned = _GH_TIMESTAMP_RE.sub("", line).strip()
        if cleaned.startswith("{"):
            result.append(cleaned)
    return result


def parse_impl_run_summary(lines: list[str]) -> ImplRunSummary:
    """Parse stream-json lines into a structured summary.

    Walks through JSONL lines from a Claude CLI session, extracting:
    - Session ID from ``system/init`` messages
    - Tool actions from ``assistant`` messages
    - Final result from ``result`` message
    - Error messages from tool results and system errors

    Args:
        lines: List of JSON strings (one per line) from Claude CLI stream-json

    Returns:
        Structured summary of the implementation run
    """
    session_id: str | None = None
    model: str | None = None
    duration_ms: int | None = None
    num_turns: int | None = None
    is_error: bool | None = None
    exit_code: int | None = None
    cost_usd: float | None = None
    tool_actions: list[ToolAction] = []
    error_messages: list[str] = []
    files_read: list[str] = []
    files_modified: list[str] = []
    assistant_messages: list[str] = []

    # Track files for deduplication
    files_read_set: set[str] = set()
    files_modified_set: set[str] = set()

    for line in lines:
        parsed = _safe_json_loads(line)
        if parsed is None:
            continue

        msg_type = parsed.get("type")
        if not isinstance(msg_type, str):
            continue

        if msg_type == "system" and parsed.get("subtype") == "init":
            session_id = _extract_str(parsed, "session_id")
            model = _extract_str(parsed, "model")

        elif msg_type == "assistant":
            _process_assistant_message(
                parsed,
                tool_actions=tool_actions,
                assistant_messages=assistant_messages,
                files_read=files_read,
                files_read_set=files_read_set,
                files_modified=files_modified,
                files_modified_set=files_modified_set,
            )

        elif msg_type == "tool_result":
            _process_tool_result(parsed, error_messages=error_messages)

        elif msg_type == "result":
            duration_ms = _extract_int(parsed, "duration_ms")
            num_turns = _extract_int(parsed, "num_turns")
            is_error = _extract_bool(parsed, "is_error")
            exit_code = _extract_int(parsed, "exit_code")
            cost_usd = _extract_float(parsed, "cost_usd")

    return ImplRunSummary(
        session_id=session_id,
        model=model,
        duration_ms=duration_ms,
        num_turns=num_turns,
        is_error=is_error,
        exit_code=exit_code,
        cost_usd=cost_usd,
        tool_actions=tool_actions,
        error_messages=error_messages,
        files_read=files_read,
        files_modified=files_modified,
        assistant_messages=assistant_messages,
    )


def format_summary(summary: ImplRunSummary) -> str:
    """Render an ImplRunSummary as human-readable text.

    Args:
        summary: The parsed summary to render

    Returns:
        Multi-line string suitable for terminal output
    """
    sections: list[str] = []

    # Header
    sections.append("=== Implementation Run Summary ===\n")

    # Session info
    info_lines: list[str] = []
    if summary.session_id is not None:
        info_lines.append(f"Session ID: {summary.session_id}")
    if summary.model is not None:
        info_lines.append(f"Model: {summary.model}")
    if summary.duration_ms is not None:
        duration_s = summary.duration_ms / 1000
        minutes = int(duration_s // 60)
        seconds = int(duration_s % 60)
        info_lines.append(f"Duration: {minutes}m {seconds}s")
    if summary.num_turns is not None:
        info_lines.append(f"Turns: {summary.num_turns}")
    if summary.cost_usd is not None:
        info_lines.append(f"Cost: ${summary.cost_usd:.2f}")
    if summary.exit_code is not None:
        info_lines.append(f"Exit Code: {summary.exit_code}")
    if summary.is_error is not None:
        info_lines.append(f"Error: {summary.is_error}")
    if info_lines:
        sections.append("\n".join(info_lines))

    # Errors
    if summary.error_messages:
        sections.append("\n--- Errors ---")
        for msg in summary.error_messages:
            sections.append(f"  - {msg}")

    # Tool actions timeline
    if summary.tool_actions:
        sections.append("\n--- Tool Actions ---")
        for action in summary.tool_actions:
            sections.append(f"  [{action.tool_name}] {action.summary}")

    # Files
    if summary.files_read:
        sections.append(f"\n--- Files Read ({len(summary.files_read)}) ---")
        for f in summary.files_read:
            sections.append(f"  {f}")

    if summary.files_modified:
        sections.append(f"\n--- Files Modified ({len(summary.files_modified)}) ---")
        for f in summary.files_modified:
            sections.append(f"  {f}")

    # Assistant messages (last few)
    if summary.assistant_messages:
        sections.append(f"\n--- Assistant Messages ({len(summary.assistant_messages)}) ---")
        # Show last 5 messages
        for msg in summary.assistant_messages[-5:]:
            sections.append(f"  > {msg}")

    return "\n".join(sections)


# --- Internal helpers ---


def _safe_json_loads(line: str) -> dict | None:
    """Parse a JSON line, returning None on failure."""
    if not line.strip():
        return None
    try:
        parsed = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _extract_str(d: dict, key: str) -> str | None:
    """Extract a string value from a dict, returning None if not a string."""
    val = d.get(key)
    if isinstance(val, str):
        return val
    return None


def _extract_int(d: dict, key: str) -> int | None:
    """Extract an int value from a dict, returning None if not an int."""
    val = d.get(key)
    if isinstance(val, int) and not isinstance(val, bool):
        return val
    return None


def _extract_float(d: dict, key: str) -> float | None:
    """Extract a float value from a dict, returning None if not numeric."""
    val = d.get(key)
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    return None


def _extract_bool(d: dict, key: str) -> bool | None:
    """Extract a bool value from a dict, returning None if not a bool."""
    val = d.get(key)
    if isinstance(val, bool):
        return val
    return None


def _truncate_message(text: str, *, max_chars: int) -> str:
    """Truncate a message to max_chars, adding ellipsis if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


_WORKTREE_PLACEHOLDER = "/placeholder"


def _process_assistant_message(
    message: dict,
    *,
    tool_actions: list[ToolAction],
    assistant_messages: list[str],
    files_read: list[str],
    files_read_set: set[str],
    files_modified: list[str],
    files_modified_set: set[str],
) -> None:
    """Process an assistant message, extracting text and tool uses."""
    # Extract text content
    text = extract_text_content(message)
    if text is not None:
        truncated = _truncate_message(text, max_chars=200)
        assistant_messages.append(truncated)

    # Extract tool uses
    content = message.get("content", [])
    if not isinstance(content, list):
        return

    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "tool_use":
            continue

        tool_name = item.get("name")
        if not isinstance(tool_name, str):
            continue

        params = item.get("input", {})
        if not isinstance(params, dict):
            params = {}

        # Track file operations
        _track_file_operation(
            tool_name,
            params,
            files_read=files_read,
            files_read_set=files_read_set,
            files_modified=files_modified,
            files_modified_set=files_modified_set,
        )

        # Build tool action summary
        summary = summarize_tool_use(item, Path(_WORKTREE_PLACEHOLDER))
        if summary is None:
            summary = _build_fallback_tool_summary(tool_name, params)

        tool_actions.append(ToolAction(tool_name=tool_name, summary=summary))


def _track_file_operation(
    tool_name: str,
    params: dict,
    *,
    files_read: list[str],
    files_read_set: set[str],
    files_modified: list[str],
    files_modified_set: set[str],
) -> None:
    """Track which files are read vs modified by tool uses."""
    file_path = params.get("file_path")
    if not isinstance(file_path, str):
        return

    if tool_name == "Read":
        if file_path not in files_read_set:
            files_read_set.add(file_path)
            files_read.append(file_path)
    elif tool_name in ("Edit", "Write"):
        if file_path not in files_modified_set:
            files_modified_set.add(file_path)
            files_modified.append(file_path)


def _build_fallback_tool_summary(tool_name: str, params: dict) -> str:
    """Build a summary for tools not covered by summarize_tool_use."""
    if tool_name == "Read":
        file_path = params.get("file_path", "")
        if isinstance(file_path, str) and file_path:
            return f"Read {file_path}"
        return "Read file"

    if tool_name == "Glob":
        pattern = params.get("pattern", "")
        if isinstance(pattern, str) and pattern:
            return f"Glob {pattern}"
        return "Glob search"

    if tool_name == "Grep":
        pattern = params.get("pattern", "")
        if isinstance(pattern, str) and pattern:
            return f"Grep: {pattern}"
        return "Grep search"

    return f"{tool_name}"


def _process_tool_result(message: dict, *, error_messages: list[str]) -> None:
    """Process a tool_result message, extracting error information."""
    is_error = message.get("is_error")
    if is_error is not True:
        return

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        truncated = _truncate_message(content.strip(), max_chars=300)
        error_messages.append(truncated)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    truncated = _truncate_message(text.strip(), max_chars=300)
                    error_messages.append(truncated)
