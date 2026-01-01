#!/usr/bin/env python3
"""
Session ID Injector Hook

This command is invoked via erk exec session-id-injector-hook.
"""

import json
import sys
import tomllib
from pathlib import Path

import click

from erk.hooks.decorators import logged_hook
from erk_shared.context.helpers import require_repo_root


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
@click.pass_context
@logged_hook
def session_id_injector_hook(ctx: click.Context) -> None:
    """Inject session ID into conversation context when relevant."""
    # Inject repo_root from context
    repo_root = require_repo_root(ctx)

    # Inline scope check: only run in erk-managed projects
    if not (repo_root / ".erk").is_dir():
        return

    # Early exit if github_planning is disabled - output nothing
    if not _is_github_planning_enabled():
        return

    # Attempt to read session context from stdin (if Claude Code provides it)
    session_id = None

    # Check if stdin has data (non-blocking)
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read().strip()
        if stdin_data:
            data = json.loads(stdin_data)
            session_id = data.get("session_id")

    # Output session ID if available
    if session_id:
        # Write to file for CLI tools to read (worktree-scoped persistence)
        session_file = repo_root / ".erk" / "scratch" / "current-session-id"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(session_id, encoding="utf-8")

        # Still output reminder for LLM context
        click.echo(f"📌 session: {session_id}")
    # If no session ID available, output nothing (hook doesn't fire unnecessarily)


if __name__ == "__main__":
    session_id_injector_hook()
