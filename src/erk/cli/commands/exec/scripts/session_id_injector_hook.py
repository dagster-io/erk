#!/usr/bin/env python3
"""
Session ID Injector Hook

This command is invoked via erk exec session-id-injector-hook.
"""

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import click

from erk.hooks.decorators import logged_hook, project_scoped


def _get_repo_root() -> Path:
    """Get the repository root via git rev-parse.

    Returns:
        Path to the git repository root.

    Raises:
        subprocess.CalledProcessError: If not in a git repository.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


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
@logged_hook
@project_scoped
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
        # Write to file for CLI tools to read (worktree-scoped persistence)
        # Must use repo root to ensure file is at correct location
        repo_root = _get_repo_root()
        session_file = repo_root / ".erk" / "scratch" / "current-session-id"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(session_id, encoding="utf-8")

        # Still output reminder for LLM context
        click.echo(f"📌 session: {session_id}")
    # If no session ID available, output nothing (hook doesn't fire unnecessarily)


if __name__ == "__main__":
    session_id_injector_hook()
