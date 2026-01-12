"""Unit tests for find_assignment_by_worktree_path utility."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.navigation_helpers import find_assignment_by_worktree_path
from erk.core.worktree_pool import PoolState, SlotAssignment


def _create_test_assignment(
    slot_name: str,
    branch_name: str,
    worktree_path: Path,
) -> SlotAssignment:
    """Create a test assignment with current timestamp."""
    return SlotAssignment(
        slot_name=slot_name,
        branch_name=branch_name,
        assigned_at=datetime.now(UTC).isoformat(),
        worktree_path=worktree_path,
    )


def testfind_assignment_by_worktree_path_finds_matching_slot(tmp_path: Path) -> None:
    """Test that find_assignment_by_worktree_path finds a matching slot assignment."""
    worktree_path = tmp_path / "worktrees" / "erk-slot-01"
    worktree_path.mkdir(parents=True)

    assignment = _create_test_assignment("erk-slot-01", "feature-branch", worktree_path)
    state = PoolState.test(assignments=(assignment,))

    result = find_assignment_by_worktree_path(state, worktree_path)

    assert result is not None
    assert result.slot_name == "erk-slot-01"
    assert result.branch_name == "feature-branch"


def testfind_assignment_by_worktree_path_returns_none_for_non_slot(tmp_path: Path) -> None:
    """Test that find_assignment_by_worktree_path returns None for non-slot worktrees."""
    slot_worktree = tmp_path / "worktrees" / "erk-slot-01"
    slot_worktree.mkdir(parents=True)
    regular_worktree = tmp_path / "worktrees" / "regular-worktree"
    regular_worktree.mkdir(parents=True)

    assignment = _create_test_assignment("erk-slot-01", "feature-branch", slot_worktree)
    state = PoolState.test(assignments=(assignment,))

    result = find_assignment_by_worktree_path(state, regular_worktree)

    assert result is None


def testfind_assignment_by_worktree_path_returns_none_for_empty_pool(tmp_path: Path) -> None:
    """Test that find_assignment_by_worktree_path returns None when pool has no assignments."""
    worktree_path = tmp_path / "worktrees" / "some-worktree"
    worktree_path.mkdir(parents=True)

    state = PoolState.test(assignments=())

    result = find_assignment_by_worktree_path(state, worktree_path)

    assert result is None


def testfind_assignment_by_worktree_path_returns_none_for_nonexistent_path(
    tmp_path: Path,
) -> None:
    """Test that find_assignment_by_worktree_path returns None for nonexistent paths."""
    slot_worktree = tmp_path / "worktrees" / "erk-slot-01"
    slot_worktree.mkdir(parents=True)
    nonexistent_path = tmp_path / "worktrees" / "nonexistent"

    assignment = _create_test_assignment("erk-slot-01", "feature-branch", slot_worktree)
    state = PoolState.test(assignments=(assignment,))

    result = find_assignment_by_worktree_path(state, nonexistent_path)

    assert result is None


def testfind_assignment_by_worktree_path_handles_multiple_assignments(tmp_path: Path) -> None:
    """Test that find_assignment_by_worktree_path finds correct assignment among multiple."""
    wt1 = tmp_path / "worktrees" / "erk-slot-01"
    wt1.mkdir(parents=True)
    wt2 = tmp_path / "worktrees" / "erk-slot-02"
    wt2.mkdir(parents=True)

    assignment1 = _create_test_assignment("erk-slot-01", "feature-a", wt1)
    assignment2 = _create_test_assignment("erk-slot-02", "feature-b", wt2)
    state = PoolState.test(assignments=(assignment1, assignment2))

    result = find_assignment_by_worktree_path(state, wt2)

    assert result is not None
    assert result.slot_name == "erk-slot-02"
    assert result.branch_name == "feature-b"
