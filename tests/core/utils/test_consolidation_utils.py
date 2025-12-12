"""Tests for consolidation utility functions.

These tests verify the pure business logic for worktree consolidation operations.
All tests are fast and don't require filesystem I/O.
"""

from pathlib import Path

import pytest

from erk.core.consolidation_utils import (
    calculate_stack_range,
    create_consolidation_plan,
    identify_removable_worktrees,
)
from erk_shared.git.abc import WorktreeInfo

# Tests for calculate_stack_range function


def test_full_stack_when_end_branch_is_none() -> None:
    """Full stack consolidation when end_branch is None."""
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    result = calculate_stack_range(stack, None)
    assert result == stack


def test_partial_stack_to_middle_branch() -> None:
    """Partial stack consolidation up to a middle branch."""
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    result = calculate_stack_range(stack, "feat-2")
    assert result == ["main", "feat-1", "feat-2"]


def test_partial_stack_to_first_branch() -> None:
    """Consolidate only up to first branch after trunk."""
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    result = calculate_stack_range(stack, "feat-1")
    assert result == ["main", "feat-1"]


def test_partial_stack_to_trunk() -> None:
    """Consolidate only trunk branch."""
    stack = ["main", "feat-1", "feat-2"]
    result = calculate_stack_range(stack, "main")
    assert result == ["main"]


def test_partial_stack_to_last_branch() -> None:
    """Consolidate up to last branch (same as full stack)."""
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    result = calculate_stack_range(stack, "feat-3")
    assert result == stack


def test_error_when_branch_not_in_stack() -> None:
    """Raises ValueError when end_branch is not in stack."""
    stack = ["main", "feat-1", "feat-2"]
    with pytest.raises(ValueError, match="Branch 'unknown' not in stack"):
        calculate_stack_range(stack, "unknown")


def test_single_branch_stack() -> None:
    """Handle stack with only trunk branch."""
    stack = ["main"]
    result = calculate_stack_range(stack, None)
    assert result == ["main"]


# Tests for identify_removable_worktrees function


def test_basic_removal_single_worktree() -> None:
    """Remove single worktree not in target."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/feat-1"), "feat-1", False),
        WorktreeInfo(Path("/repo/feat-2"), "feat-2", False),
    ]
    stack = ["main", "feat-1", "feat-2"]
    target = Path("/repo/feat-1")

    result = identify_removable_worktrees(worktrees, stack, target)

    assert len(result) == 1
    assert result[0].path == Path("/repo/feat-2")
    assert result[0].branch == "feat-2"


def test_never_remove_root_worktree() -> None:
    """Root worktree is never removed even if in stack."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/feat-1"), "feat-1", False),
    ]
    stack = ["main", "feat-1"]
    target = Path("/repo/feat-1")

    result = identify_removable_worktrees(worktrees, stack, target)

    # Only feat-1's worktree is removed, not root
    assert len(result) == 0  # feat-1 is target, root is protected


def test_never_remove_target_worktree() -> None:
    """Target worktree is never removed."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/feat-1"), "feat-1", False),
        WorktreeInfo(Path("/repo/feat-2"), "feat-2", False),
    ]
    stack = ["main", "feat-1", "feat-2"]
    target = Path("/repo/feat-2")

    result = identify_removable_worktrees(worktrees, stack, target)

    # feat-2 is target, so only feat-1 is removable (root is protected)
    assert len(result) == 1
    assert result[0].branch == "feat-1"


def test_skip_worktrees_with_detached_head() -> None:
    """Worktrees in detached HEAD state are skipped."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/feat-1"), "feat-1", False),
        WorktreeInfo(Path("/repo/detached"), None, False),  # Detached HEAD
    ]
    stack = ["main", "feat-1"]
    target = Path("/repo")

    result = identify_removable_worktrees(worktrees, stack, target)

    # Only feat-1 is removable (detached and root are excluded)
    assert len(result) == 1
    assert result[0].branch == "feat-1"


def test_skip_worktrees_not_in_consolidation_range() -> None:
    """Only remove worktrees in the consolidation range."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/feat-1"), "feat-1", False),
        WorktreeInfo(Path("/repo/feat-2"), "feat-2", False),
        WorktreeInfo(Path("/repo/feat-3"), "feat-3", False),
    ]
    stack = ["main", "feat-1"]  # Only consolidating up to feat-1
    target = Path("/repo")

    result = identify_removable_worktrees(worktrees, stack, target)

    # Only feat-1 is in range and removable (feat-2, feat-3 not in stack range)
    assert len(result) == 1
    assert result[0].branch == "feat-1"


def test_exclude_source_worktree_when_creating_new() -> None:
    """Source worktree is excluded when creating new worktree with --name."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/current"), "feat-1", False),
        WorktreeInfo(Path("/repo/other"), "feat-2", False),
    ]
    stack = ["main", "feat-1", "feat-2"]
    target = Path("/repo/new")
    source = Path("/repo/current")

    result = identify_removable_worktrees(worktrees, stack, target, source)

    # Source worktree is excluded, only "other" is removable
    assert len(result) == 1
    assert result[0].path == Path("/repo/other")


def test_empty_result_when_no_removable_worktrees() -> None:
    """Empty list when no worktrees are removable."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
    ]
    stack = ["main"]
    target = Path("/repo")

    result = identify_removable_worktrees(worktrees, stack, target)

    assert len(result) == 0


def test_multiple_removable_worktrees() -> None:
    """Multiple worktrees can be removed."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/feat-1"), "feat-1", False),
        WorktreeInfo(Path("/repo/feat-2"), "feat-2", False),
        WorktreeInfo(Path("/repo/feat-3"), "feat-3", False),
    ]
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    target = Path("/repo")

    result = identify_removable_worktrees(worktrees, stack, target)

    # All non-root worktrees in stack are removable
    assert len(result) == 3
    branches = [wt.branch for wt in result]
    assert set(branches) == {"feat-1", "feat-2", "feat-3"}


# Tests for create_consolidation_plan function


def test_full_consolidation_plan() -> None:
    """Create plan for full stack consolidation."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/feat-1"), "feat-1", False),
        WorktreeInfo(Path("/repo/feat-2"), "feat-2", False),
    ]
    stack = ["main", "feat-1", "feat-2"]
    target = Path("/repo")

    plan = create_consolidation_plan(worktrees, stack, None, target)

    assert plan.stack_branches == stack
    assert plan.stack_to_consolidate == stack  # Full stack
    assert len(plan.worktrees_to_remove) == 2
    assert plan.target_worktree_path == target
    assert plan.source_worktree_path is None


def test_partial_consolidation_plan() -> None:
    """Create plan for partial stack consolidation."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/feat-1"), "feat-1", False),
        WorktreeInfo(Path("/repo/feat-2"), "feat-2", False),
        WorktreeInfo(Path("/repo/feat-3"), "feat-3", False),
    ]
    stack = ["main", "feat-1", "feat-2", "feat-3"]
    target = Path("/repo/feat-1")

    plan = create_consolidation_plan(worktrees, stack, "feat-2", target)

    assert plan.stack_branches == stack  # Full stack for context
    assert plan.stack_to_consolidate == ["main", "feat-1", "feat-2"]  # Partial
    # Only feat-2's worktree is removable
    # (target is feat-1, root is protected, feat-3 not in range)
    assert len(plan.worktrees_to_remove) == 1
    assert plan.worktrees_to_remove[0].branch == "feat-2"


def test_plan_with_new_worktree_creation() -> None:
    """Create plan when using --name to create new worktree."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/current"), "feat-1", False),
    ]
    stack = ["main", "feat-1"]
    target = Path("/repo/new")
    source = Path("/repo/current")

    plan = create_consolidation_plan(worktrees, stack, None, target, source)

    assert plan.target_worktree_path == target
    assert plan.source_worktree_path == source
    # No removable worktrees (source is excluded, root is protected)
    assert len(plan.worktrees_to_remove) == 0


def test_plan_validates_branch_argument() -> None:
    """Plan raises error when end_branch is invalid."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
    ]
    stack = ["main", "feat-1"]
    target = Path("/repo")

    with pytest.raises(ValueError, match="Branch 'unknown' not in stack"):
        create_consolidation_plan(worktrees, stack, "unknown", target)


def test_immutable_plan_object() -> None:
    """ConsolidationPlan is frozen (immutable)."""
    worktrees = [WorktreeInfo(Path("/repo"), "main", True)]
    stack = ["main"]
    target = Path("/repo")

    plan = create_consolidation_plan(worktrees, stack, None, target)

    # Verify frozen dataclass
    with pytest.raises(AttributeError):
        plan.stack_branches = ["different"]  # type: ignore[misc]
