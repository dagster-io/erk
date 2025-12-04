#!/usr/bin/env python3
"""
Session ID Injector Hook

Injects the current session ID into conversation context for /erk:enhance-and-save-plan.
This command is invoked via dot-agent run erk session-id-injector-hook.
"""

import json
import sys
import tomllib
from pathlib import Path

import click


def _is_github_planning_enabled() -> bool:
    """Check if github_planning is enabled in ~/.erk/config.toml.

    Returns True (enabled) if config doesn't exist or flag is missing.
    """
    config_path = Path.home() / ".erk" / "config.toml"
    if not config_path.exists():
        return True  # Default enabled

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    return bool(data.get("github_planning", True))


@click.command(name="session-id-injector-hook")
def session_id_injector_hook() -> None:
    """Inject session ID into conversation context when relevant."""
    # Early exit if github_planning is disabled - output nothing
    if not _is_github_planning_enabled():
        return

    # Attempt to read session context from stdin (if Claude Code provides it)
    session_id = None

    try:
        # Check if stdin has data (non-blocking)
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                context = json.loads(stdin_data)
                session_id = context.get("session_id")
    except (json.JSONDecodeError, Exception):
        # If stdin reading fails, continue without session ID
        pass

    # Output session ID if available
    if session_id:
        click.echo("<reminder>")
        click.echo(f"SESSION_CONTEXT: session_id={session_id}")
        click.echo("</reminder>")
    # If no session ID available, output nothing (hook doesn't fire unnecessarily)


if __name__ == "__main__":
    session_id_injector_hook()
