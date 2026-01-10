"""Checkout navigation helpers - shared across checkout commands.

This module is separate from navigation_helpers.py to avoid circular imports.
navigation_helpers imports from wt.create_cmd, which triggers wt/__init__.py,
which imports wt.checkout_cmd. By having checkout-specific helpers here,
we break that cycle.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

import click

from erk.cli.activation import render_activation_script
from erk.core.context import ErkContext
from erk_shared.output.output import user_output


def _is_bot_author(author: str) -> bool:
    """Check if commit author is a known bot (e.g., github-actions[bot])."""
    return "[bot]" in author.lower()


def format_sync_status(ahead: int, behind: int) -> str | None:
    """Format sync status as arrows, or None if in sync.

    Args:
        ahead: Number of commits ahead of origin
        behind: Number of commits behind origin

    Returns:
        Formatted string like "1↑", "2↓", "1↑ 3↓", or None if in sync
    """
    if ahead == 0 and behind == 0:
        return None  # In sync, nothing to report
    parts: list[str] = []
    if ahead > 0:
        parts.append(f"{ahead}↑")
    if behind > 0:
        parts.append(f"{behind}↓")
    return " ".join(parts)


def display_sync_status(
    ctx: ErkContext,
    *,
    worktree_path: Path,
    branch: str,
    script: bool,
) -> None:
    """Display sync status after checkout if not in sync with remote.

    Shows appropriate message based on sync state:
    - In sync: No output
    - Ahead: "Local is X↑ ahead of origin (X unpushed commit(s))"
    - Behind: "Local is X↓ behind origin (run 'git pull' to update)"
    - Diverged: Warning with instructions

    Args:
        ctx: Erk context with git operations
        worktree_path: Path to the worktree
        branch: Branch name
        script: Whether running in script mode (suppresses educational output)
    """
    # Script mode: suppress educational output for machine-readability
    if script:
        return

    ahead, behind = ctx.git.get_ahead_behind(worktree_path, branch)
    sync_display = format_sync_status(ahead, behind)

    if sync_display is None:
        return  # In sync, nothing to report

    # Format message based on sync state
    if ahead > 0 and behind > 0:
        # Diverged - most important case, needs warning
        warning = click.style("⚠ Local has diverged from origin:", fg="yellow")
        styled_sync = click.style(sync_display, fg="yellow", bold=True)
        user_output(f"  {warning} {styled_sync}")
        user_output(
            "  Run 'git fetch && git status' to see details, "
            "or 'git reset --hard origin/<branch>' to sync"
        )
    elif ahead > 0:
        # Ahead only
        commit_word = "commit" if ahead == 1 else "commits"
        styled_sync = click.style(sync_display, fg="cyan")
        user_output(f"  Local is {styled_sync} ahead of origin ({ahead} unpushed {commit_word})")
    else:
        # Behind only - check if commits are from bots (e.g., autofix)
        behind_authors = ctx.git.get_behind_commit_authors(worktree_path, branch)
        has_bot_commits = any(_is_bot_author(author) for author in behind_authors)

        styled_sync = click.style(sync_display, fg="yellow")
        if has_bot_commits:
            user_output(f"  Local is {styled_sync} behind origin - remote has autofix commits")
        else:
            user_output(f"  Local is {styled_sync} behind origin (run 'git pull' to update)")


def navigate_to_worktree(
    ctx: ErkContext,
    *,
    worktree_path: Path,
    branch: str,
    script: bool,
    command_name: str,
    script_message: str,
    relative_path: Path | None,
    post_cd_commands: Sequence[str] | None,
) -> bool:
    """Navigate to worktree, handling script/subshell/shell-integration modes.

    This function consolidates the three-mode navigation pattern used by checkout commands:
    1. Script mode: Generate activation script and output for shell integration
    2. No shell integration: Spawn a subshell in the worktree directory
    3. Shell integration active: Return True so caller can output custom message

    Args:
        ctx: Erk context (for script_writer and shell gateway)
        worktree_path: Path to the target worktree directory
        branch: Branch name (for subshell display)
        script: Whether running in script mode
        command_name: Name of the command (for script generation)
        script_message: Message to echo in activation script (e.g., 'echo "Switched to worktree"')
        relative_path: Computed relative path to preserve directory position, or None
        post_cd_commands: Optional shell commands to run after cd

    Returns:
        True if caller should output custom message (shell integration mode).
        In script and subshell modes, this function exits via sys.exit() and does not return.
    """
    from erk.cli.subshell import is_shell_integration_active, spawn_simple_subshell

    if script:
        activation_script = render_activation_script(
            worktree_path=worktree_path,
            target_subpath=relative_path,
            post_cd_commands=post_cd_commands,
            final_message=script_message,
            comment="work activate-script",
        )
        result = ctx.script_writer.write_activation_script(
            activation_script,
            command_name=command_name,
            comment=f"checkout {branch}",
        )
        result.output_for_shell_integration()
        sys.exit(0)
    elif not is_shell_integration_active():
        exit_code = spawn_simple_subshell(
            ctx.shell,
            worktree_path=worktree_path,
            branch=branch,
            shell=None,
        )
        sys.exit(exit_code)
    else:
        return True  # Caller should output custom message
