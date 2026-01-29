#!/usr/bin/env python3
"""PreToolUse hook for dignified-python reminders when editing .py files.

Reads tool_input.file_path from stdin JSON and emits a dignified-python
reminder if the file is a Python file and the capability is installed.

Exit codes:
    0: Always (never blocks tool execution)

This command is invoked via:
    ERK_HOOK_ID=pre-tool-use-hook erk exec pre-tool-use-hook
"""

import json
import sys

import click

from erk.core.capabilities.detection import is_reminder_installed
from erk.hooks.decorators import HookContext, hook_command

# ============================================================================
# Pure Functions
# ============================================================================


def extract_file_path_from_stdin(stdin_json: str) -> str | None:
    """Extract tool_input.file_path from PreToolUse stdin JSON.

    Args:
        stdin_json: Raw JSON string from stdin.

    Returns:
        The file_path value if present, None otherwise.
    """
    if not stdin_json.strip():
        return None
    data = json.loads(stdin_json)
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str):
        return None
    return file_path if file_path else None


def is_python_file(file_path: str | None) -> bool:
    """Check if file_path has a .py extension.

    Args:
        file_path: The file path to check, or None.

    Returns:
        True if the file path ends with .py, False otherwise.
    """
    if file_path is None:
        return False
    return file_path.endswith(".py")


def build_pretool_dignified_python_reminder() -> str:
    """Return the dignified-python reminder text for PreToolUse hooks.

    Returns:
        Static reminder string about dignified-python coding standards.
    """
    return (
        "dignified-python: Editing Python file. "
        "LBYL (no try/except control flow), no default params, "
        "frozen dataclasses, pathlib only. "
        "See AGENTS.md 'Python Standards' for full rules."
    )


# ============================================================================
# Main Hook Entry Point
# ============================================================================


@hook_command(name="pre-tool-use-hook")
def pre_tool_use_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
    """PreToolUse hook for dignified-python reminders on .py file edits.

    This hook runs before Write/Edit tool calls. It checks whether the
    target file is a Python file and emits a coding standards reminder.

    Exit codes:
        0: Always (informational only, never blocks)
    """
    if not hook_ctx.is_erk_project:
        return

    stdin_data = sys.stdin.read()
    file_path = extract_file_path_from_stdin(stdin_data)

    if not is_python_file(file_path):
        return

    if not is_reminder_installed(hook_ctx.repo_root, "dignified-python"):
        return

    click.echo(build_pretool_dignified_python_reminder())


if __name__ == "__main__":
    pre_tool_use_hook()
