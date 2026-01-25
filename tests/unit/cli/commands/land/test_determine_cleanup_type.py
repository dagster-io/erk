"""Unit tests for determine_cleanup_type().

Tests each CleanupType variant to verify correct classification
of cleanup scenarios. Pure unit tests — no fakes needed, only tmp_path
for pool.json file I/O.
"""

from pathlib import Path

from erk.cli.commands.land_cmd import (
    CleanupType,
    determine_cleanup_type,
)
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    save_pool_state,
)


class TestDetermineCleanupType:
    def test_no_delete_returns_no_delete(self, tmp_path: Path) -> None:
        result = determine_cleanup_type(
            no_delete=True,
            worktree_path=tmp_path / "erk-slot-01",
            pool_json_path=tmp_path / "pool.json",
            branch="feature-branch",
        )
        assert result.cleanup_type == CleanupType.NO_DELETE
        assert result.pool_state is None
        assert result.assignment is None

    def test_no_worktree_returns_no_worktree(self, tmp_path: Path) -> None:
        result = determine_cleanup_type(
            no_delete=False,
            worktree_path=None,
            pool_json_path=tmp_path / "pool.json",
            branch="feature-branch",
        )
        assert result.cleanup_type == CleanupType.NO_WORKTREE
        assert result.pool_state is None
        assert result.assignment is None

    def test_slot_with_assignment_returns_slot_assigned(self, tmp_path: Path) -> None:
        pool_json = tmp_path / "pool.json"
        state = PoolState.test(
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-branch",
                    assigned_at="2026-01-25T00:00:00Z",
                    worktree_path=tmp_path / "erk-slot-01",
                ),
            ),
        )
        save_pool_state(pool_json, state)

        result = determine_cleanup_type(
            no_delete=False,
            worktree_path=tmp_path / "erk-slot-01",
            pool_json_path=pool_json,
            branch="feature-branch",
        )
        assert result.cleanup_type == CleanupType.SLOT_ASSIGNED
        assert result.pool_state is not None
        assert result.assignment is not None
        assert result.assignment.branch_name == "feature-branch"

    def test_slot_without_assignment_returns_slot_unassigned(self, tmp_path: Path) -> None:
        pool_json = tmp_path / "pool.json"
        state = PoolState.test()
        save_pool_state(pool_json, state)

        result = determine_cleanup_type(
            no_delete=False,
            worktree_path=tmp_path / "erk-slot-01",
            pool_json_path=pool_json,
            branch="feature-branch",
        )
        assert result.cleanup_type == CleanupType.SLOT_UNASSIGNED
        assert result.assignment is None

    def test_non_slot_worktree_returns_non_slot(self, tmp_path: Path) -> None:
        pool_json = tmp_path / "pool.json"
        state = PoolState.test()
        save_pool_state(pool_json, state)

        result = determine_cleanup_type(
            no_delete=False,
            worktree_path=tmp_path / "my-feature-worktree",
            pool_json_path=pool_json,
            branch="feature-branch",
        )
        assert result.cleanup_type == CleanupType.NON_SLOT
        assert result.assignment is None
