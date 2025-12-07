"""Utility functions for worktree operations.

This module provides pure business logic functions for worktree operations,
separated from I/O and CLI concerns. These functions work with data objects
(WorktreeInfo) and enable fast unit testing.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from erk_shared.git.abc import WorktreeInfo


class MoveOperationType(Enum):
    """Type of move operation to perform between worktrees."""

    MOVE = "move"  # Source has branch, target doesn't exist or is detached
    SWAP = "swap"  # Both source and target have branches
    CREATE = "create"  # Target doesn't exist


@dataclass(frozen=True)
class MoveOperation:
    """Represents a move operation between worktrees.

    Attributes:
        operation_type: Type of operation (move, swap, or create)
        source_path: Path to source worktree
        target_path: Path to target worktree
        source_branch: Branch in source worktree (None if detached)
        target_branch: Branch in target worktree (None if doesn't exist or detached)
    """

    operation_type: MoveOperationType
    source_path: Path
    target_path: Path
    source_branch: str | None
    target_branch: str | None


def compute_relative_path_in_worktree(
    worktrees: list[WorktreeInfo],
    current_dir: Path,
) -> Path | None:
    """Compute relative path from current worktree root to current_dir.

    Used to preserve the user's relative position when switching worktrees.
    For example, if the user is at /repo/worktrees/feat/src/lib, switching
    to another worktree should land them at <target>/src/lib if it exists.

    Args:
        worktrees: List of WorktreeInfo objects to search
        current_dir: Current directory path (will be resolved internally)

    Returns:
        Relative path from worktree root to current_dir, or None if:
        - current_dir is at the worktree root (relative path would be '.')
        - current_dir is not within any known worktree

    Examples:
        >>> worktrees = [WorktreeInfo(Path("/repo/wt/feat"), "feat", False)]
        >>> compute_relative_path_in_worktree(worktrees, Path("/repo/wt/feat/src/lib"))
        Path("src/lib")
        >>> compute_relative_path_in_worktree(worktrees, Path("/repo/wt/feat"))
        None  # At worktree root
    """
    worktree_root = find_worktree_containing_path(worktrees, current_dir)
    if worktree_root is None:
        return None

    # Resolve both paths for reliable comparison
    resolved_current = current_dir.resolve()
    resolved_root = worktree_root.resolve()

    # If at worktree root, return None (no relative subpath)
    if resolved_current == resolved_root:
        return None

    # Compute relative path
    relative = resolved_current.relative_to(resolved_root)

    return relative


def find_worktree_containing_path(worktrees: list[WorktreeInfo], target_path: Path) -> Path | None:
    """Find which worktree contains the given path.

    Returns the most specific (deepest) match to handle nested worktrees correctly.
    Handles symlink resolution differences (e.g., /var vs /private/var on macOS).

    Args:
        worktrees: List of WorktreeInfo objects to search
        target_path: Path to check (will be resolved internally)

    Returns:
        Path to the worktree that contains target_path, or None if not found

    Examples:
        >>> worktrees = [WorktreeInfo(Path("/repo"), "main", True),
        ...              WorktreeInfo(Path("/repo/erks/feat"), "feat", False)]
        >>> find_worktree_containing_path(worktrees, Path("/repo/erks/feat/src"))
        Path("/repo/erks/feat")  # Returns deepest match
    """
    best_match: Path | None = None
    best_match_depth = -1

    # Resolve target_path to handle symlinks consistently
    resolved_target = target_path.resolve()

    for wt in worktrees:
        wt_path = wt.path.resolve()

        # Check if target_path is within this worktree
        # is_relative_to() returns True if target_path is under wt_path
        if resolved_target.is_relative_to(wt_path):
            # Count path depth to find most specific match
            depth = len(wt_path.parts)
            if depth > best_match_depth:
                best_match = wt_path
                best_match_depth = depth

    return best_match


def find_current_worktree(worktrees: list[WorktreeInfo], current_dir: Path) -> WorktreeInfo | None:
    """Find the WorktreeInfo object for the worktree containing current_dir.

    Higher-level wrapper around find_worktree_containing_path that returns
    the full WorktreeInfo object instead of just the path.

    Args:
        worktrees: List of WorktreeInfo objects to search
        current_dir: Current directory path (should be resolved)

    Returns:
        WorktreeInfo object if found, None if not in any worktree

    Examples:
        >>> worktrees = [WorktreeInfo(Path("/repo"), "main", True)]
        >>> find_current_worktree(worktrees, Path("/repo/src"))
        WorktreeInfo(path=Path("/repo"), branch="main", is_root=True)
    """
    wt_path = find_worktree_containing_path(worktrees, current_dir)
    if wt_path is None:
        return None

    # Find and return the matching WorktreeInfo object
    for wt in worktrees:
        if wt.path.resolve() == wt_path:
            return wt

    return None


def is_root_worktree(worktree_path: Path, repo_root: Path) -> bool:
    """Check if a worktree path is the repository root worktree.

    Compares resolved paths to determine if the worktree is the root.

    Args:
        worktree_path: Path to the worktree to check
        repo_root: Path to the repository root

    Returns:
        True if worktree_path is the root worktree, False otherwise

    Examples:
        >>> is_root_worktree(Path("/repo"), Path("/repo"))
        True
        >>> is_root_worktree(Path("/repo/erks/feat"), Path("/repo"))
        False
    """
    return worktree_path.resolve() == repo_root.resolve()


def get_worktree_branch(worktrees: list[WorktreeInfo], wt_path: Path) -> str | None:
    """Get the branch checked out in a worktree.

    Returns None if worktree is not found or is in detached HEAD state.

    Args:
        worktrees: List of WorktreeInfo objects to search
        wt_path: Path to the worktree

    Returns:
        Branch name if found and checked out, None otherwise

    Examples:
        >>> worktrees = [WorktreeInfo(Path("/repo/erks/feat"), "feature-x", False)]
        >>> get_worktree_branch(worktrees, Path("/repo/erks/feat"))
        "feature-x"
        >>> get_worktree_branch(worktrees, Path("/repo/erks/other"))
        None
    """
    # Resolve paths for comparison to handle relative vs absolute paths
    wt_path_resolved = wt_path.resolve()
    for wt in worktrees:
        if wt.path.resolve() == wt_path_resolved:
            return wt.branch
    return None


def find_worktree_with_branch(worktrees: list[WorktreeInfo], branch: str) -> Path | None:
    """Find the worktree path containing the specified branch.

    Returns None if the branch is not found in any worktree.

    Args:
        worktrees: List of WorktreeInfo objects to search
        branch: Branch name to find

    Returns:
        Path to worktree containing the branch, or None if not found

    Examples:
        >>> worktrees = [WorktreeInfo(Path("/repo/erks/feat"), "feature-x", False)]
        >>> find_worktree_with_branch(worktrees, "feature-x")
        Path("/repo/erks/feat")
        >>> find_worktree_with_branch(worktrees, "unknown")
        None
    """
    for wt in worktrees:
        if wt.branch == branch:
            return wt.path
    return None


def filter_non_trunk_branches(all_branches: dict[str, Any], stack: list[str]) -> list[str]:
    """Filter out trunk branches from a stack.

    Args:
        all_branches: Dictionary mapping branch names to branch info (with is_trunk attribute)
        stack: List of branch names to filter

    Returns:
        List of non-trunk branches from the stack

    Examples:
        >>> branches = {"main": BranchInfo(is_trunk=True), "feat": BranchInfo(is_trunk=False)}
        >>> filter_non_trunk_branches(branches, ["main", "feat"])
        ["feat"]
    """
    return [b for b in stack if b in all_branches and not all_branches[b].is_trunk]


def determine_move_operation(
    worktrees: list[WorktreeInfo],
    source_path: Path,
    target_path: Path,
) -> MoveOperation:
    """Determine the type of move operation based on source and target states.

    Pure function that analyzes worktree states to determine operation type:
    - CREATE: Target doesn't exist
    - SWAP: Both source and target have branches
    - MOVE: Source has branch, target exists but is detached or doesn't exist

    Args:
        worktrees: List of all worktrees in the repository
        source_path: Path to source worktree (must exist)
        target_path: Path to target worktree (may not exist)

    Returns:
        MoveOperation object describing the operation to perform

    Examples:
        >>> worktrees = [
        ...     WorktreeInfo(Path("/repo/src"), "feat-1", False, False),
        ... ]
        >>> determine_move_operation(worktrees, Path("/repo/src"), Path("/repo/new"))
        MoveOperation(operation_type=MoveOperationType.CREATE, ...)
    """
    # Get source branch
    source_branch = get_worktree_branch(worktrees, source_path)

    # Check if target exists in worktrees list
    target_branch = get_worktree_branch(worktrees, target_path)

    # Determine operation type
    if target_branch is None:
        # Target doesn't exist or is detached
        # Check if any worktree exists at target_path
        target_exists = any(wt.path.resolve() == target_path.resolve() for wt in worktrees)
        if target_exists:
            operation_type = MoveOperationType.MOVE
        else:
            operation_type = MoveOperationType.CREATE
    else:
        # Target exists with a branch - this is a swap
        operation_type = MoveOperationType.SWAP

    return MoveOperation(
        operation_type=operation_type,
        source_path=source_path,
        target_path=target_path,
        source_branch=source_branch,
        target_branch=target_branch,
    )
