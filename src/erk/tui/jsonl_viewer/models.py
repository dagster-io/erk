"""Data models for JSONL viewer."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class JsonlEntry:
    """Represents a single entry from a JSONL file."""

    line_number: int
    entry_type: str
    role: str | None
    tool_name: str | None
    raw_json: str
    parsed: dict


def extract_tool_name(entry: dict) -> str | None:
    """Extract tool name from tool_use content blocks.

    Args:
        entry: Parsed JSON entry

    Returns:
        Tool name if found, None otherwise
    """
    message = entry.get("message")
    if not isinstance(message, dict):
        return None

    content = message.get("content")
    if not isinstance(content, list):
        return None

    # Find first tool_use block
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            name = block.get("name")
            if isinstance(name, str):
                return name

    return None


def format_summary(entry: JsonlEntry) -> str:
    """Format entry summary for display.

    Format: [line#] type | tool_name?

    Args:
        entry: JSONL entry to format

    Returns:
        Formatted summary string
    """
    line_str = f"[{entry.line_number:>4}]"

    parts = [line_str, entry.entry_type]
    if entry.tool_name:
        parts.append(entry.tool_name)

    return " | ".join(parts)


def parse_jsonl_file(path: Path) -> list[JsonlEntry]:
    """Parse JSONL file into list of entries.

    Skips empty lines and malformed JSON.

    Args:
        path: Path to JSONL file

    Returns:
        List of parsed entries
    """
    entries: list[JsonlEntry] = []
    content = path.read_text(encoding="utf-8")

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        if not isinstance(parsed, dict):
            continue

        entry_type = parsed.get("type", "unknown")
        if not isinstance(entry_type, str):
            entry_type = "unknown"

        # Extract role from message if present
        role: str | None = None
        message = parsed.get("message")
        if isinstance(message, dict):
            msg_role = message.get("role")
            if isinstance(msg_role, str):
                role = msg_role

        tool_name = extract_tool_name(parsed)

        entries.append(
            JsonlEntry(
                line_number=line_number,
                entry_type=entry_type,
                role=role,
                tool_name=tool_name,
                raw_json=stripped,
                parsed=parsed,
            )
        )

    return entries
