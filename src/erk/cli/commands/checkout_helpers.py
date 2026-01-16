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

from erk.cli.activation import (
    ENABLE_ACTIVATION_SCRIPTS,
    ensure_worktree_activate_script,
    render_activation_script,
)
from erk.cli.commands.slot.common import allocate_slot_for_branch
from erk.cli.core import worktree_path_for
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext
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


def ensure_branch_has_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    branch_name: str,
    no_slot: bool,
    force: bool,
) -> tuple[Path, bool]:
    """Ensure branch has a worktree, creating if needed.

    Checks if the branch is already checked out in a worktree.
    If not, creates a worktree using either slot allocation or direct path.

    Args:
        ctx: Erk context with git operations
        repo: Repository context with worktrees directory
        branch_name: Name of the branch to checkout
        no_slot: If True, create worktree without slot assignment
        force: Auto-unassign oldest branch if pool is full

    Returns:
        Tuple of (worktree_path, already_existed) where already_existed
        is True if the branch was already in a worktree.
    """
    # Check if branch already exists in a worktree
    existing = ctx.git.find_worktree_for_branch(repo.root, branch_name)
    if existing is not None:
        return existing, True

    # Create worktree (with or without slot)
    if no_slot:
        worktree_path = worktree_path_for(repo.worktrees_dir, branch_name)
        ctx.git.add_worktree(
            repo.root,
            worktree_path,
            branch=branch_name,
            ref=None,
            create_branch=False,
        )
    else:
        result = allocate_slot_for_branch(
            ctx,
            repo,
            branch_name,
            force=force,
            reuse_inactive_slots=True,
            cleanup_artifacts=True,
        )
        worktree_path = result.worktree_path
        if not result.already_assigned:
            user_output(click.style(f"✓ Assigned {branch_name} to {result.slot_name}", fg="green"))

    # Write activation script for newly created worktrees
    if ENABLE_ACTIVATION_SCRIPTS:
        ensure_worktree_activate_script(
            worktree_path=worktree_path,
            post_create_commands=None,
        )

    return worktree_path, False


def navigate_and_display_checkout(
    ctx: ErkContext,
    *,
    worktree_path: Path,
    branch_name: str,
    script: bool,
    command_name: str,
    already_existed: bool,
    existing_message: str,
    new_message: str,
    script_message_existing: str,
    script_message_new: str,
) -> None:
    """Navigate to worktree and display checkout status.

    Handles the navigation and output display for checkout commands.
    Formats the messages with {styled_path} placeholder for the worktree path.

    Args:
        ctx: Erk context with git operations
        worktree_path: Path to the worktree
        branch_name: Name of the branch
        script: Whether running in script mode
        command_name: Name of the command for script generation
        already_existed: Whether the worktree already existed
        existing_message: Message for existing worktree (use {styled_path} placeholder)
        new_message: Message for new worktree (use {styled_path} placeholder)
        script_message_existing: Script message for existing worktree
        script_message_new: Script message for new worktree
    """
    styled_path = click.style(str(worktree_path), fg="cyan", bold=True)

    should_output = navigate_to_worktree(
        ctx,
        worktree_path=worktree_path,
        branch=branch_name,
        script=script,
        command_name=command_name,
        script_message=script_message_existing if already_existed else script_message_new,
        relative_path=None,
        post_cd_commands=None,
    )

    if should_output:
        message = existing_message if already_existed else new_message
        user_output(message.format(styled_path=styled_path))
        display_sync_status(ctx, worktree_path=worktree_path, branch=branch_name, script=script)
