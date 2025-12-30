"""Shell completion functions for CLI commands.

Separated from navigation_helpers to avoid circular imports.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import click

from erk.cli.core import discover_repo_context
from erk.core.repo_discovery import ensure_erk_metadata_dir

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from erk.core.context import ErkContext


@contextmanager
def shell_completion_context(ctx: click.Context) -> Generator[ErkContext]:
    """Context manager for shell completion that provides ErkContext with error handling.

    Combines context extraction with graceful error handling for shell completion.
    Suppresses all exceptions for graceful degradation.

    Why this is needed:
    - Shell completion runs in the user's interactive shell session
    - Any uncaught exception would break the shell experience with a Python traceback
    - Click's shell completion protocol expects functions to return empty lists on error
    - This allows tab-completion to fail gracefully without disrupting the user

    Usage:
        with shell_completion_context(ctx) as erk_ctx:
            # ... completion logic
            return completion_candidates
        return []  # Fallback if exception

    Reference:
        Click's shell completion protocol:
        https://click.palletsprojects.com/en/stable/shell-completion/
    """
    try:
        yield ctx.find_root().obj
    except Exception:
        # Suppress exceptions for graceful degradation, but log for debugging
        # Shell completion should never break the user's shell experience
        logger.debug("Shell completion error", exc_info=True)


def complete_worktree_names(
    ctx: click.Context, param: click.Parameter | None, incomplete: str
) -> list[str]:
    """Shell completion for worktree names. Includes 'root' for the repository root.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete
    """
    with shell_completion_context(ctx) as erk_ctx:
        repo = discover_repo_context(erk_ctx, erk_ctx.cwd)
        ensure_erk_metadata_dir(repo)

        names = ["root"] if "root".startswith(incomplete) else []

        # Get worktree names from git_ops instead of filesystem iteration
        worktrees = erk_ctx.git.list_worktrees(repo.root)
        for wt in worktrees:
            if wt.is_root:
                continue  # Skip root worktree (already added as "root")
            worktree_name = wt.path.name
            if worktree_name.startswith(incomplete):
                names.append(worktree_name)

        return names
    return []


def complete_branch_names(
    ctx: click.Context, param: click.Parameter | None, incomplete: str
) -> list[str]:
    """Shell completion for branch names. Includes both local and remote branches.

    Remote branch names have their remote prefix stripped
    (e.g., 'origin/feature' becomes 'feature').
    Duplicates are removed if a branch exists both locally and remotely.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete
    """
    with shell_completion_context(ctx) as erk_ctx:
        repo = discover_repo_context(erk_ctx, erk_ctx.cwd)
        ensure_erk_metadata_dir(repo)

        # Collect all branch names in a set for deduplication
        branch_names = set()

        # Add local branches
        local_branches = erk_ctx.git.list_local_branches(repo.root)
        branch_names.update(local_branches)

        # Add remote branches with prefix stripped
        remote_branches = erk_ctx.git.list_remote_branches(repo.root)
        for remote_branch in remote_branches:
            # Strip remote prefix (e.g., 'origin/feature' -> 'feature')
            if "/" in remote_branch:
                _, branch_name = remote_branch.split("/", 1)
                branch_names.add(branch_name)
            else:
                # Fallback: if no slash, use as-is
                branch_names.add(remote_branch)

        # Filter by incomplete prefix and return sorted list
        matching_branches = [name for name in branch_names if name.startswith(incomplete)]
        return sorted(matching_branches)
    return []


def complete_plan_files(
    ctx: click.Context, param: click.Parameter | None, incomplete: str
) -> list[str]:
    """Shell completion for plan files (markdown files in current directory).

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete

    Returns:
        List of completion candidates (filenames matching incomplete text)
    """
    with shell_completion_context(ctx) as erk_ctx:
        # Get current working directory from erk context
        cwd = erk_ctx.cwd

        # Find all .md files in current directory
        candidates = []
        for md_file in cwd.glob("*.md"):
            # Filter by incomplete prefix if provided
            if md_file.name.startswith(incomplete):
                candidates.append(md_file.name)

        return sorted(candidates)
    return []
