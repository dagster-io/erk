"""Pure business logic for worktree consolidation operations.

This module contains the core logic for determining which worktrees can be
safely consolidated (removed) when consolidating a worktree stack into a
single worktree. All functions are pure and testable without filesystem I/O.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.git.abc import WorktreeInfo


@dataclass(frozen=True)
class ConsolidationPlan:
    """Plan for consolidating worktrees in a stack.

    Attributes:
        stack_branches: Full list of branches in the stack (trunk to leaf)
        stack_to_consolidate: Subset of branches being consolidated
        worktrees_to_remove: Worktrees that will be removed
        target_worktree_path: Path to the target worktree (where branches will be consolidated)
        source_worktree_path: Path to source worktree (None if not creating new worktree)
    """

    stack_branches: list[str]
    stack_to_consolidate: list[str]
    worktrees_to_remove: list[WorktreeInfo]
    target_worktree_path: Path
    source_worktree_path: Path | None


def calculate_stack_range(
    stack_branches: list[str],
    end_branch: str | None,
) -> list[str]:
    """Calculate which portion of the stack to consolidate.

    Args:
        stack_branches: Full stack from trunk to leaf (e.g., ['main', 'feat-1', 'feat-2', 'feat-3'])
        end_branch: Optional branch name to consolidate up to (inclusive).
                   If None, consolidate entire stack.

    Returns:
        List of branches to consolidate, from trunk up to (and including) end_branch.
        If end_branch is None, returns the full stack.

    Raises:
        ValueError: If end_branch is not in stack_branches

    Examples:
        >>> calculate_stack_range(['main', 'feat-1', 'feat-2', 'feat-3'], 'feat-2')
        ['main', 'feat-1', 'feat-2']

        >>> calculate_stack_range(['main', 'feat-1', 'feat-2'], None)
        ['main', 'feat-1', 'feat-2']
    """
    if end_branch is None:
        return stack_branches

    if end_branch not in stack_branches:
        raise ValueError(f"Branch '{end_branch}' not in stack")

    branch_index = stack_branches.index(end_branch)
    return stack_branches[: branch_index + 1]


def identify_removable_worktrees(
    all_worktrees: list[WorktreeInfo],
    stack_to_consolidate: list[str],
    target_worktree_path: Path,
    source_worktree_path: Path | None = None,
) -> list[WorktreeInfo]:
    """Identify which worktrees can be safely removed during consolidation.

    A worktree is removable if:
    1. It has a branch checked out (not detached HEAD)
    2. Its branch is in the consolidation range
    3. It's not the target worktree
    4. It's not the source worktree (if creating new worktree with --name)
    5. It's not the root worktree (CRITICAL safety check)

    Args:
        all_worktrees: All worktrees in the repository
        stack_to_consolidate: Branches being consolidated
        target_worktree_path: Path to target worktree (will not be removed)
        source_worktree_path: Path to source worktree when creating new worktree
                             (will be removed separately, not included in result)

    Returns:
        List of worktrees that can be safely removed

    Examples:
        >>> worktrees = [
        ...     WorktreeInfo(Path('/repo'), 'main', True, False),
        ...     WorktreeInfo(Path('/repo/feat-1'), 'feat-1', False, False),
        ...     WorktreeInfo(Path('/repo/feat-2'), 'feat-2', False, False),
        ... ]
        >>> identify_removable_worktrees(
        ...     worktrees,
        ...     ['main', 'feat-1', 'feat-2'],
        ...     Path('/repo/feat-1'),
        ...     None
        ... )
        [WorktreeInfo(path=Path('/repo/feat-2'), branch='feat-2', is_root=False, is_bare=False)]
    """
    removable: list[WorktreeInfo] = []
    target_resolved = target_worktree_path.resolve()
    source_resolved = source_worktree_path.resolve() if source_worktree_path else None

    for worktree in all_worktrees:
        # Skip if no branch (detached HEAD)
        if worktree.branch is None:
            continue

        # Skip if branch is not in the consolidation range
        if worktree.branch not in stack_to_consolidate:
            continue

        # Skip the target worktree
        if worktree.path.resolve() == target_resolved:
            continue

        # Skip source worktree if creating new worktree (will be removed separately)
        if source_resolved is not None and worktree.path.resolve() == source_resolved:
            continue

        # Never remove root worktree (CRITICAL safety check)
        if worktree.is_root:
            continue

        removable.append(worktree)

    return removable


def create_consolidation_plan(
    *,
    all_worktrees: list[WorktreeInfo],
    stack_branches: list[str],
    end_branch: str | None,
    target_worktree_path: Path,
    source_worktree_path: Path | None = None,
) -> ConsolidationPlan:
    """Create a complete consolidation plan.

    This is a convenience function that combines calculate_stack_range() and
    identify_removable_worktrees() into a single operation.

    Args:
        all_worktrees: All worktrees in the repository
        stack_branches: Full stack from trunk to leaf
        end_branch: Optional branch to consolidate up to (inclusive)
        target_worktree_path: Path to target worktree
        source_worktree_path: Path to source worktree (when creating new with --name)

    Returns:
        Complete consolidation plan with all information needed for execution

    Raises:
        ValueError: If end_branch is not in stack_branches
    """
    stack_to_consolidate = calculate_stack_range(stack_branches, end_branch)

    worktrees_to_remove = identify_removable_worktrees(
        all_worktrees,
        stack_to_consolidate,
        target_worktree_path,
        source_worktree_path,
    )

    return ConsolidationPlan(
        stack_branches=stack_branches,
        stack_to_consolidate=stack_to_consolidate,
        worktrees_to_remove=worktrees_to_remove,
        target_worktree_path=target_worktree_path,
        source_worktree_path=source_worktree_path,
    )
