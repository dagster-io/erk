"""Shell completion functions for CLI commands.

Separated from navigation_helpers to avoid circular imports.
"""

from collections.abc import Generator
from contextlib import contextmanager

import click

from erk.cli.core import discover_repo_context
from erk.core.context import create_context
from erk.core.repo_discovery import ensure_erk_metadata_dir


@contextmanager
def shell_completion_error_boundary() -> Generator[None]:
    """Context manager for shell completion error boundaries.

    Shell completion functions are acceptable error boundaries per Click's protocol.
    This context manager provides graceful error handling for shell completion by
    suppressing all exceptions and allowing completion to return an empty list.

    Why this is needed:
    - Shell completion runs in the user's interactive shell session
    - Any uncaught exception would break the shell experience with a Python traceback
    - Click's shell completion protocol expects functions to return empty lists on error
    - This allows tab-completion to fail gracefully without disrupting the user

    Usage:
        with shell_completion_error_boundary():
            # Shell completion logic here
            # Any exception will be suppressed
            return completion_candidates

    Reference:
        Click's shell completion protocol:
        https://click.palletsprojects.com/en/stable/shell-completion/
    """
    try:
        yield
    except Exception:
        # Suppress all exceptions for graceful degradation
        # Shell completion should never break the user's shell experience
        pass


def complete_worktree_names(
    ctx: click.Context, param: click.Parameter | None, incomplete: str
) -> list[str]:
    """Shell completion for worktree names. Includes 'root' for the repository root.

    Uses shell_completion_error_boundary for graceful error handling.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete
    """
    with shell_completion_error_boundary():
        # During shell completion, ctx.obj may be None if the CLI group callback
        # hasn't run yet. Create a default context in this case.
        erk_ctx = ctx.find_root().obj
        if erk_ctx is None:
            erk_ctx = create_context(dry_run=False)

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

    Uses shell_completion_error_boundary for graceful error handling.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete
    """
    with shell_completion_error_boundary():
        # During shell completion, ctx.obj may be None if the CLI group callback
        # hasn't run yet. Create a default context in this case.
        erk_ctx = ctx.find_root().obj
        if erk_ctx is None:
            erk_ctx = create_context(dry_run=False)

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

    Uses shell_completion_error_boundary for graceful error handling.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete

    Returns:
        List of completion candidates (filenames matching incomplete text)
    """
    with shell_completion_error_boundary():
        # During shell completion, ctx.obj may be None if the CLI group callback
        # hasn't run yet. Create a default context in this case.
        erk_ctx = ctx.find_root().obj
        if erk_ctx is None:
            erk_ctx = create_context(dry_run=False)

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


def complete_objective_names(
    ctx: click.Context, param: click.Parameter | None, incomplete: str
) -> list[str]:
    """Shell completion for objective names.

    Uses shell_completion_error_boundary for graceful error handling.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete

    Returns:
        List of completion candidates (objective names matching incomplete text)
    """
    with shell_completion_error_boundary():
        # During shell completion, ctx.obj may be None if the CLI group callback
        # hasn't run yet. Create a default context in this case.
        erk_ctx = ctx.find_root().obj
        if erk_ctx is None:
            erk_ctx = create_context(dry_run=False)

        repo = discover_repo_context(erk_ctx, erk_ctx.cwd)

        # Get objective names from store
        objectives = erk_ctx.objectives.list_objectives(repo.root)

        # Filter by incomplete prefix
        return [name for name in objectives if name.startswith(incomplete)]
    return []
