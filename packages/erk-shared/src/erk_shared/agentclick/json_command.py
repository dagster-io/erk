"""JSON output utilities for CLI commands.

Provides:
- emit_json() for structured JSON output with success=True
- emit_json_result() for serializing result objects via to_json_dict() protocol
- read_stdin_json() for reading JSON from piped stdin
"""

import dataclasses
import json
import sys
from typing import Any

import click


def read_stdin_json() -> dict[str, Any] | None:
    """Read a JSON object from stdin if piped. Returns None if stdin is a TTY or empty.

    Raises:
        json.JSONDecodeError: If stdin contains invalid JSON
        ValueError: If stdin JSON is not an object
    """
    if sys.stdin.isatty():
        return None
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON input must be an object")
    return data


def emit_json(data: dict[str, Any]) -> None:
    """Emit a JSON success result to stdout. Adds success=True automatically."""
    data["success"] = True
    click.echo(json.dumps(data, indent=2))


def emit_json_result(result: Any) -> None:
    """Emit a structured result as JSON.

    Calls result.to_json_dict() if available, falls back to
    dataclasses.asdict() for plain dataclasses.

    Raises:
        TypeError: If result has no to_json_dict() and is not a dataclass
    """
    if hasattr(result, "to_json_dict"):
        data = result.to_json_dict()
    elif dataclasses.is_dataclass(result) and not isinstance(result, type):
        data = dataclasses.asdict(result)
    else:
        type_name = type(result).__name__
        raise TypeError(f"Cannot serialize {type_name}: no to_json_dict() and not a dataclass")
    emit_json(data)
