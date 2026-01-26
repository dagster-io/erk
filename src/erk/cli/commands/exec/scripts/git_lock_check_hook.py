#!/usr/bin/env python3
"""Git Lock Check Hook.

This PreToolUse hook cleans stale git index.lock files before Bash commands
run. This prevents "fatal: Unable to create '.git/index.lock': File exists"
errors that occur when git operations are interrupted mid-execution.

Exit codes:
    0: Success (always allows the Bash command to proceed)

Detection heuristic:
    - A lock file is considered stale if it's 0 bytes (git writes content when active)
    - Non-zero byte lock files are left alone (git is likely running)

This command is invoked via:
    erk exec git-lock-check-hook
"""

import click

from erk.hooks.decorators import HookContext, hook_command
from erk_shared.git.lock import get_lock_path


def is_stale_lock(lock_path_size: int) -> bool:
    """Check if a lock file is stale based on its size.

    Git writes content to the lock file when it's actively using it.
    A 0-byte lock file indicates it was created but never written to,
    which happens when git is interrupted between creating and using the lock.

    Args:
        lock_path_size: Size of the lock file in bytes

    Returns:
        True if the lock appears to be stale (0 bytes)
    """
    return lock_path_size == 0


@hook_command(name="git-lock-check-hook")
def git_lock_check_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
    """Clean stale git index.lock before Bash commands.

    This PreToolUse hook runs before every Bash command to check for and
    remove stale git index.lock files. This prevents git operations from
    failing due to leftover lock files from interrupted operations.

    Exit codes:
        0: Always succeeds (allows Bash command to proceed)
    """
    # Scope check: only run in erk-managed projects
    if not hook_ctx.is_erk_project:
        return

    lock_path = get_lock_path(hook_ctx.repo_root)
    if lock_path is None:
        # Not a git repository, nothing to check
        return

    if not lock_path.exists():
        # No lock file present
        return

    # Check if lock is stale (0-byte = stale, git writes content when active)
    lock_size = lock_path.stat().st_size
    if is_stale_lock(lock_size):
        lock_path.unlink()
        click.echo(f"Cleaned stale git index.lock: {lock_path}", err=True)

    # Always exit 0 to allow command to proceed


if __name__ == "__main__":
    git_lock_check_hook()
