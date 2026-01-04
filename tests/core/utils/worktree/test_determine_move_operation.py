"""Tests for determine_move_operation function."""

from pathlib import Path

import pytest

from erk.core.worktree_utils import MoveOperationType, determine_move_operation
from erk_shared.git.abc import WorktreeInfo


def test_create_operation_when_target_doesnt_exist() -> None:
    """Test CREATE operation when target worktree doesn't exist."""
    worktrees = [
        WorktreeInfo(Path("/repo/source"), "feat-1", False),
    ]
    source = Path("/repo/source")
    target = Path("/repo/new")

    operation = determine_move_operation(worktrees, source, target)

    assert operation.operation_type == MoveOperationType.CREATE
    assert operation.source_path == source
    assert operation.target_path == target
    assert operation.source_branch == "feat-1"
    assert operation.target_branch is None


def test_move_operation_when_target_is_detached() -> None:
    """Test MOVE operation when target exists but is detached HEAD."""
    worktrees = [
        WorktreeInfo(Path("/repo/source"), "feat-1", False),
        WorktreeInfo(Path("/repo/target"), None, False),  # Detached
    ]
    source = Path("/repo/source")
    target = Path("/repo/target")

    operation = determine_move_operation(worktrees, source, target)

    assert operation.operation_type == MoveOperationType.MOVE
    assert operation.source_branch == "feat-1"
    assert operation.target_branch is None


def test_swap_operation_when_both_have_branches() -> None:
    """Test SWAP operation when both source and target have branches."""
    worktrees = [
        WorktreeInfo(Path("/repo/source"), "feat-1", False),
        WorktreeInfo(Path("/repo/target"), "feat-2", False),
    ]
    source = Path("/repo/source")
    target = Path("/repo/target")

    operation = determine_move_operation(worktrees, source, target)

    assert operation.operation_type == MoveOperationType.SWAP
    assert operation.source_branch == "feat-1"
    assert operation.target_branch == "feat-2"


def test_source_in_detached_head_state() -> None:
    """Test when source worktree is in detached HEAD."""
    worktrees = [
        WorktreeInfo(Path("/repo/source"), None, False),  # Detached
        WorktreeInfo(Path("/repo/target"), "feat-1", False),
    ]
    source = Path("/repo/source")
    target = Path("/repo/target")

    operation = determine_move_operation(worktrees, source, target)

    assert operation.source_branch is None
    assert operation.target_branch == "feat-1"
    # Would still be SWAP since target has branch
    assert operation.operation_type == MoveOperationType.SWAP


def test_move_from_root_worktree() -> None:
    """Test moving from root worktree to new location."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
    ]
    source = Path("/repo")
    target = Path("/repo/new")

    operation = determine_move_operation(worktrees, source, target)

    assert operation.operation_type == MoveOperationType.CREATE
    assert operation.source_branch == "main"
    assert operation.target_branch is None


def test_immutable_move_operation() -> None:
    """Test that MoveOperation is frozen (immutable)."""
    worktrees = [
        WorktreeInfo(Path("/repo/source"), "feat-1", False),
    ]

    operation = determine_move_operation(worktrees, Path("/repo/source"), Path("/repo/new"))

    # Verify frozen dataclass
    with pytest.raises(AttributeError):
        operation.operation_type = MoveOperationType.SWAP  # type: ignore[misc] -- intentionally mutating frozen dataclass to test immutability


def test_multiple_worktrees_only_relevant_ones_checked() -> None:
    """Test that only source and target worktrees matter."""
    worktrees = [
        WorktreeInfo(Path("/repo"), "main", True),
        WorktreeInfo(Path("/repo/other1"), "feat-1", False),
        WorktreeInfo(Path("/repo/source"), "feat-2", False),
        WorktreeInfo(Path("/repo/other2"), "feat-3", False),
        WorktreeInfo(Path("/repo/target"), "feat-4", False),
    ]
    source = Path("/repo/source")
    target = Path("/repo/target")

    operation = determine_move_operation(worktrees, source, target)

    assert operation.operation_type == MoveOperationType.SWAP
    assert operation.source_branch == "feat-2"
    assert operation.target_branch == "feat-4"


def test_resolved_paths_for_comparison() -> None:
    """Test that paths are resolved for comparison."""
    worktrees = [
        WorktreeInfo(Path("/repo/source"), "feat-1", False),
        WorktreeInfo(Path("/repo/target"), "feat-2", False),
    ]
    # Use relative path that resolves to same location
    source = Path("/repo/source")
    target = Path("/repo/../repo/target")  # Same as /repo/target

    operation = determine_move_operation(worktrees, source, target)

    assert operation.operation_type == MoveOperationType.SWAP
