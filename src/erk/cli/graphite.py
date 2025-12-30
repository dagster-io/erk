"""Graphite integration for erk.

Graphite (https://graphite.com) is a stacked git workflow tool that allows developers
to manage dependent branches in linear stacks. This module provides utility functions
for working with worktree stacks.

For comprehensive gt mental model and command reference, see:
.agent/GT_MENTAL_MODEL.md

## What is Graphite?

Graphite organizes branches into "stacks" - linear chains of dependent branches built
on top of each other. For example:

    main (trunk)
      └─ feature/phase-1
           └─ feature/phase-2
                └─ feature/phase-3

Each branch in the stack depends on its parent, making it easy to work on multiple
related changes while keeping them in separate PRs.

## Graphite Abstraction

This module uses the Graphite abstraction to read Graphite cache data. Production
code should use ctx.graphite_ops methods directly instead of importing functions from
this module.

See erk.core.graphite_ops for the abstraction interface.
"""

from pathlib import Path

from erk.core.context import ErkContext
from erk_shared.git.abc import WorktreeInfo


def find_worktrees_containing_branch(
    ctx: ErkContext,
    repo_root: Path,
    worktrees: list[WorktreeInfo],
    target_branch: str,
) -> list[WorktreeInfo]:
    """Find all worktrees that have target_branch checked out (exact match only).

    Args:
        ctx: Erk context with git operations
        repo_root: Path to the repository root
        worktrees: List of all worktrees from list_worktrees()
        target_branch: Branch name to search for

    Returns:
        List of WorktreeInfo objects where target_branch is checked out.
        Empty list if no worktrees have the branch checked out.

    Algorithm:
        1. For each worktree:
           a. Get the worktree's checked-out branch
           b. Skip worktrees with detached HEAD (branch=None)
           c. Check if worktree.branch == target_branch (exact string match)
           d. If yes, add worktree to results
        2. Return all matching worktrees

    Example:
        >>> worktrees = ctx.git_ops.list_worktrees(repo.root)
        >>> matching = find_worktrees_containing_branch(ctx, repo.root, worktrees, "feature-2")
        >>> print([wt.path for wt in matching])
        [Path("/path/to/work/feature-work")]
    """
    matching_worktrees: list[WorktreeInfo] = []

    for wt in worktrees:
        # Skip worktrees with detached HEAD
        if wt.branch is None:
            continue

        # Check if target_branch is exactly checked out in this worktree
        if wt.branch == target_branch:
            matching_worktrees.append(wt)

    return matching_worktrees
