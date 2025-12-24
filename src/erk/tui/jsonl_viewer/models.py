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


def _interpret_escape_sequences(text: str) -> str:
    """Convert literal escape sequences to actual characters.

    Converts \\n, \\t, \\r to their actual character equivalents.

    Args:
        text: Text with literal escape sequences

    Returns:
        Text with actual newlines, tabs, carriage returns
    """
    return text.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")


def _format_as_yaml_like(value: object, indent: int = 0) -> str:
    """Format a value in YAML-like style for readability.

    Args:
        value: Value to format (dict, list, str, int, float, bool, None)
        indent: Current indentation level

    Returns:
        Formatted string representation
    """
    prefix = "  " * indent

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, str):
        # Interpret escape sequences - no additional formatting for strings
        return _interpret_escape_sequences(value)

    if isinstance(value, list):
        if not value:
            return "[]"
        lines = []
        for item in value:
            formatted_item = _format_as_yaml_like(item, indent + 1)
            if "\n" in formatted_item:
                # Multi-line item
                first_line, *rest = formatted_item.split("\n")
                lines.append(f"{prefix}- {first_line}")
                lines.extend(rest)
            else:
                lines.append(f"{prefix}- {formatted_item}")
        return "\n".join(lines)

    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for k, v in value.items():
            formatted_v = _format_as_yaml_like(v, indent + 1)
            if "\n" in formatted_v:
                # Multi-line value
                first_line, *rest = formatted_v.split("\n")
                lines.append(f"{prefix}{k}: {first_line}")
                lines.extend(rest)
            else:
                lines.append(f"{prefix}{k}: {formatted_v}")
        return "\n".join(lines)

    # Fallback for unknown types
    return str(value)


def format_entry_detail(entry: JsonlEntry, formatted: bool = True) -> str:
    """Format entry detail for display.

    Args:
        entry: JSONL entry to format
        formatted: If True, use YAML-like formatting. If False, use raw JSON.

    Returns:
        Formatted string representation
    """
    if not formatted:
        return entry.raw_json

    return _format_as_yaml_like(entry.parsed)


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
