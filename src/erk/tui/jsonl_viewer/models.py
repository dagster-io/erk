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


def format_entry_detail(entry: JsonlEntry, formatted: bool) -> str:
    """Format entry for display in raw or formatted mode.

    Args:
        entry: JSONL entry to format
        formatted: If True, interpret escape sequences; if False, show raw JSON

    Returns:
        Formatted string for display
    """
    if not formatted:
        return json.dumps(entry.parsed, indent=2)

    # Formatted mode: render escape sequences in string values
    return _format_value(entry.parsed, indent=0)


def _format_value(value: object, indent: int) -> str:
    """Recursively format a value as readable YAML-like output.

    Args:
        value: Value to format (dict, list, string, etc.)
        indent: Current indentation level

    Returns:
        Human-readable string representation (no JSON syntax)
    """
    indent_str = "  " * indent

    if isinstance(value, dict):
        if not value:
            return "{}"
        lines: list[str] = []
        for k, v in value.items():
            formatted_v = _format_value(v, indent + 1)
            if isinstance(v, (dict, list)) and v:
                # Complex value on next line
                lines.append(f"{indent_str}{k}:")
                lines.append(formatted_v)
            else:
                # Simple value on same line
                lines.append(f"{indent_str}{k}: {formatted_v}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return "[]"
        lines = []
        for item in value:
            formatted_item = _format_value(item, indent + 1)
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{indent_str}-")
                lines.append(formatted_item)
            else:
                lines.append(f"{indent_str}- {formatted_item}")
        return "\n".join(lines)

    if isinstance(value, str):
        # Interpret escape sequences and return unquoted
        return _interpret_escape_sequences(value)

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _interpret_escape_sequences(text: str) -> str:
    """Interpret common escape sequences in a string.

    Args:
        text: String potentially containing escape sequences

    Returns:
        String with escape sequences rendered as actual characters
    """
    # Replace common escape sequences
    result = text.replace("\\n", "\n")
    result = result.replace("\\t", "\t")
    result = result.replace("\\r", "\r")
    return result


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
