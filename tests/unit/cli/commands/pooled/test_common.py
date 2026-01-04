"""Unit tests for pooled common module utilities."""

from pathlib import Path

from erk.cli.commands.pooled.common import (
    DEFAULT_POOL_SIZE,
    find_oldest_assignment,
    get_pool_size,
)
from erk.cli.config import LoadedConfig
from erk.core.context import context_for_test
from erk.core.worktree_pool import PoolState, SlotAssignment


class TestGetPoolSize:
    """Tests for get_pool_size function."""

    def test_returns_default_when_no_config(self) -> None:
        """Returns DEFAULT_POOL_SIZE when local_config is None."""
        ctx = context_for_test(local_config=None)

        result = get_pool_size(ctx)

        assert result == DEFAULT_POOL_SIZE

    def test_returns_default_when_pool_size_not_set(self) -> None:
        """Returns DEFAULT_POOL_SIZE when pool_size is None in config."""
        ctx = context_for_test(local_config=LoadedConfig.test())

        result = get_pool_size(ctx)

        assert result == DEFAULT_POOL_SIZE

    def test_returns_configured_pool_size(self) -> None:
        """Returns configured pool_size when set."""
        ctx = context_for_test(local_config=LoadedConfig.test(pool_size=8))

        result = get_pool_size(ctx)

        assert result == 8

    def test_returns_small_pool_size(self) -> None:
        """Returns small configured pool_size."""
        ctx = context_for_test(local_config=LoadedConfig.test(pool_size=2))

        result = get_pool_size(ctx)

        assert result == 2


class TestFindOldestAssignment:
    """Tests for find_oldest_assignment function."""

    def test_returns_none_for_empty_state(self) -> None:
        """Returns None when no assignments exist."""
        state = PoolState(version="1.0", pool_size=4, assignments=())

        result = find_oldest_assignment(state)

        assert result is None

    def test_returns_only_assignment(self) -> None:
        """Returns the single assignment when only one exists."""
        assignment = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-01"),
        )
        state = PoolState(version="1.0", pool_size=4, assignments=(assignment,))

        result = find_oldest_assignment(state)

        assert result == assignment

    def test_returns_oldest_by_timestamp(self) -> None:
        """Returns assignment with earliest assigned_at timestamp."""
        oldest = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-old",
            assigned_at="2024-01-01T10:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-01"),
        )
        middle = SlotAssignment(
            slot_name="erk-managed-wt-02",
            branch_name="feature-mid",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-02"),
        )
        newest = SlotAssignment(
            slot_name="erk-managed-wt-03",
            branch_name="feature-new",
            assigned_at="2024-01-01T14:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-03"),
        )
        # Assignments in non-chronological order to test sorting
        state = PoolState(version="1.0", pool_size=4, assignments=(newest, oldest, middle))

        result = find_oldest_assignment(state)

        assert result == oldest
        assert result.branch_name == "feature-old"
