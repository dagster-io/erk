#!/usr/bin/env python3
"""Auto-select sessions based on branch context.

This command takes the output of `list-sessions` and applies selection logic
to determine which sessions should be used for extraction workflows.

Usage:
    dot-agent run erk list-sessions | dot-agent run erk select-sessions

Output:
    JSON object with success status, selected sessions, and selection mode

Exit Codes:
    0: Success
    1: Error (invalid input or no sessions)

Examples:
    $ dot-agent run erk list-sessions | dot-agent run erk select-sessions
    {
      "success": true,
      "selected_sessions": [
        {"session_id": "abc123", "path": "/path/abc123.jsonl"}
      ],
      "selection_mode": "auto_substantial",
      "message": "Auto-selected 1 substantial session (current is trivial)"
    }
"""

import json
import sys
from pathlib import Path

import click

# Threshold for "trivial" sessions (under 1KB is considered trivial)
TRIVIAL_SIZE_THRESHOLD = 1024


def auto_select_sessions(
    list_sessions_output: dict,
    trivial_threshold: int = TRIVIAL_SIZE_THRESHOLD,
) -> dict:
    """Apply selection logic to determine which sessions to use.

    Selection Logic:
    1. If on trunk: current session only
    2. If current is trivial (<1KB) AND substantial sessions exist: auto-select substantial
    3. If current is substantial: use current only

    Args:
        list_sessions_output: Output from list-sessions command
        trivial_threshold: Size in bytes below which a session is trivial

    Returns:
        Dict with selected_sessions, selection_mode, and message
    """
    branch_context = list_sessions_output.get("branch_context", {})
    sessions = list_sessions_output.get("sessions", [])
    current_session_id = list_sessions_output.get("current_session_id")
    project_dir = list_sessions_output.get("project_dir", "")

    # Case 1: On trunk - current session only
    if branch_context.get("is_on_trunk", False):
        current_session = None
        for session in sessions:
            if session.get("session_id") == current_session_id:
                current_session = session
                break

        if current_session is not None:
            session_path = str(Path(project_dir) / f"{current_session_id}.jsonl")
            return {
                "selected_sessions": [
                    {
                        "session_id": current_session_id,
                        "path": session_path,
                        "size_bytes": current_session.get("size_bytes", 0),
                        "summary": current_session.get("summary", ""),
                    }
                ],
                "selection_mode": "trunk_current_only",
                "message": "On trunk branch, using current session only",
            }
        else:
            return {
                "selected_sessions": [],
                "selection_mode": "trunk_no_current",
                "message": "On trunk branch but no current session found",
            }

    # Find current session info
    current_session = None
    for session in sessions:
        if session.get("session_id") == current_session_id:
            current_session = session
            break

    # Determine if current is trivial
    current_is_trivial = True
    if current_session is not None:
        current_is_trivial = current_session.get("size_bytes", 0) < trivial_threshold

    # Find substantial sessions
    substantial_sessions = [s for s in sessions if s.get("size_bytes", 0) >= trivial_threshold]

    # Case 2: Current is trivial AND substantial sessions exist
    if current_is_trivial and substantial_sessions:
        selected = []
        for session in substantial_sessions:
            session_id = session.get("session_id", "")
            session_path = str(Path(project_dir) / f"{session_id}.jsonl")
            selected.append(
                {
                    "session_id": session_id,
                    "path": session_path,
                    "size_bytes": session.get("size_bytes", 0),
                    "summary": session.get("summary", ""),
                }
            )

        return {
            "selected_sessions": selected,
            "selection_mode": "auto_substantial",
            "message": f"Auto-selected {len(selected)} substantial session(s) (current is trivial)",
        }

    # Case 3: Current is substantial - use current only
    if current_session is not None and not current_is_trivial:
        session_path = str(Path(project_dir) / f"{current_session_id}.jsonl")
        return {
            "selected_sessions": [
                {
                    "session_id": current_session_id,
                    "path": session_path,
                    "size_bytes": current_session.get("size_bytes", 0),
                    "summary": current_session.get("summary", ""),
                }
            ],
            "selection_mode": "current_substantial",
            "message": "Using current session (substantial)",
        }

    # Fallback: No sessions to select
    if current_session is not None:
        session_path = str(Path(project_dir) / f"{current_session_id}.jsonl")
        return {
            "selected_sessions": [
                {
                    "session_id": current_session_id,
                    "path": session_path,
                    "size_bytes": current_session.get("size_bytes", 0),
                    "summary": current_session.get("summary", ""),
                }
            ],
            "selection_mode": "fallback_current",
            "message": "Using current session (only option)",
        }

    return {
        "selected_sessions": [],
        "selection_mode": "no_sessions",
        "message": "No sessions available for selection",
    }


@click.command(name="select-sessions")
def select_sessions() -> None:
    """Auto-select sessions based on branch context.

    Reads JSON from list-sessions command via stdin and applies selection logic:
    1. If on trunk: current session only
    2. If current is trivial (<1KB) AND substantial sessions exist: auto-select substantial
    3. If current is substantial: use current only
    """
    # Read from stdin
    if sys.stdin.isatty():
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "No input provided",
                    "help": "Pipe list-sessions output to this command",
                }
            )
        )
        raise SystemExit(1)

    input_text = sys.stdin.read()

    # Parse JSON input
    try:
        list_sessions_output = json.loads(input_text)
    except json.JSONDecodeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON input: {e}",
                    "help": "Input must be valid JSON from list-sessions command",
                }
            )
        )
        raise SystemExit(1) from e

    # Validate input structure
    if not list_sessions_output.get("success", False):
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "Input indicates failure from list-sessions",
                    "help": "Ensure list-sessions command succeeded",
                }
            )
        )
        raise SystemExit(1)

    # Apply selection logic
    selection_result = auto_select_sessions(list_sessions_output)

    result = {
        "success": True,
        **selection_result,
    }

    click.echo(json.dumps(result, indent=2))
