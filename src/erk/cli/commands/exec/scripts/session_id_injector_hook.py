#!/usr/bin/env python3
"""
Session ID Injector Hook

This command is invoked via erk exec session-id-injector-hook.
"""

import tomllib
from pathlib import Path

import click

from erk.hooks.decorators import HookContext, hook_command


def _is_github_planning_enabled() -> bool:
    """Check if github_planning is enabled in ~/.erk/config.toml.

    Returns True (enabled) if config doesn't exist or flag is missing.
    """
    config_path = Path.home() / ".erk" / "config.toml"
    if not config_path.exists():
        return True  # Default enabled

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    return bool(data.get("github_planning", True))


@hook_command(name="session-id-injector-hook")
def session_id_injector_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
    """Inject session ID into conversation context when relevant."""
    # Scope check: only run in erk-managed projects
    if not hook_ctx.is_erk_project:
        return

    # Early exit if github_planning is disabled - output nothing
    if not _is_github_planning_enabled():
        return

    # Output session ID if available
    if hook_ctx.session_id is not None:
        # Write to file for CLI tools to read (worktree-scoped persistence)
        session_file = hook_ctx.repo_root / ".erk" / "scratch" / "current-session-id"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(hook_ctx.session_id, encoding="utf-8")

        # Still output reminder for LLM context
        click.echo(f"📌 session: {hook_ctx.session_id}")
    # If no session ID available, output nothing (hook doesn't fire unnecessarily)


if __name__ == "__main__":
    session_id_injector_hook()
