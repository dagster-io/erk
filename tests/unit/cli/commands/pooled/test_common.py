"""Unit tests for pooled common module utilities."""

from pathlib import Path

from erk.cli.commands.pooled.common import (
    DEFAULT_POOL_SIZE,
    find_inactive_slot,
    find_oldest_assignment,
    generate_placeholder_branch_name,
    get_pool_size,
    get_slot_number_from_name,
    is_slot_initialized,
)
from erk.cli.config import LoadedConfig
from erk.core.context import context_for_test
from erk.core.worktree_pool import PoolState, SlotAssignment, SlotInfo


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
        state = PoolState(version="1.0", pool_size=4, assignments=(), slots=())

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
        state = PoolState(version="1.0", pool_size=4, assignments=(assignment,), slots=())

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
        state = PoolState(
            version="1.0", pool_size=4, assignments=(newest, oldest, middle), slots=()
        )

        result = find_oldest_assignment(state)

        assert result == oldest
        assert result.branch_name == "feature-old"


class TestGeneratePlaceholderBranchName:
    """Tests for generate_placeholder_branch_name function."""

    def test_single_digit_slot(self) -> None:
        """Generates correct name for single digit slot number."""
        result = generate_placeholder_branch_name(1)
        assert result == "__erk-slot-01-placeholder__"

    def test_double_digit_slot(self) -> None:
        """Generates correct name for double digit slot number."""
        result = generate_placeholder_branch_name(12)
        assert result == "__erk-slot-12-placeholder__"


class TestGetSlotNumberFromName:
    """Tests for get_slot_number_from_name function."""

    def test_valid_slot_name(self) -> None:
        """Returns slot number for valid slot name."""
        result = get_slot_number_from_name("erk-managed-wt-01")
        assert result == 1

    def test_double_digit_slot_name(self) -> None:
        """Returns slot number for double digit slot name."""
        result = get_slot_number_from_name("erk-managed-wt-12")
        assert result == 12

    def test_invalid_slot_name(self) -> None:
        """Returns None for invalid slot name."""
        result = get_slot_number_from_name("not-a-slot")
        assert result is None

    def test_partial_match(self) -> None:
        """Returns None for partial match."""
        result = get_slot_number_from_name("erk-managed-wt-")
        assert result is None


class TestIsSlotInitialized:
    """Tests for is_slot_initialized function."""

    def test_returns_false_for_empty_slots(self) -> None:
        """Returns False when slots list is empty."""
        state = PoolState(version="1.0", pool_size=4, assignments=(), slots=())

        result = is_slot_initialized(state, "erk-managed-wt-01")

        assert result is False

    def test_returns_true_when_slot_in_list(self) -> None:
        """Returns True when slot is in the slots list."""
        slot = SlotInfo(name="erk-managed-wt-01")
        state = PoolState(version="1.0", pool_size=4, assignments=(), slots=(slot,))

        result = is_slot_initialized(state, "erk-managed-wt-01")

        assert result is True

    def test_returns_false_when_slot_not_in_list(self) -> None:
        """Returns False when slot is not in the slots list."""
        slot = SlotInfo(name="erk-managed-wt-01")
        state = PoolState(version="1.0", pool_size=4, assignments=(), slots=(slot,))

        result = is_slot_initialized(state, "erk-managed-wt-02")

        assert result is False


class TestFindInactiveSlot:
    """Tests for find_inactive_slot function."""

    def test_returns_none_for_empty_slots(self) -> None:
        """Returns None when no slots are initialized."""
        state = PoolState(version="1.0", pool_size=4, assignments=(), slots=())

        result = find_inactive_slot(state)

        assert result is None

    def test_returns_slot_when_no_assignments(self) -> None:
        """Returns first slot when there are no assignments."""
        slot1 = SlotInfo(name="erk-managed-wt-01")
        slot2 = SlotInfo(name="erk-managed-wt-02")
        state = PoolState(version="1.0", pool_size=4, assignments=(), slots=(slot1, slot2))

        result = find_inactive_slot(state)

        assert result is not None
        assert result.name == "erk-managed-wt-01"

    def test_returns_none_when_all_slots_assigned(self) -> None:
        """Returns None when all slots have assignments."""
        slot1 = SlotInfo(name="erk-managed-wt-01")
        assignment1 = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-01"),
        )
        state = PoolState(version="1.0", pool_size=4, assignments=(assignment1,), slots=(slot1,))

        result = find_inactive_slot(state)

        assert result is None

    def test_returns_unassigned_slot(self) -> None:
        """Returns the first unassigned slot."""
        slot1 = SlotInfo(name="erk-managed-wt-01")
        slot2 = SlotInfo(name="erk-managed-wt-02")
        assignment1 = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-01"),
        )
        state = PoolState(
            version="1.0", pool_size=4, assignments=(assignment1,), slots=(slot1, slot2)
        )

        result = find_inactive_slot(state)

        assert result is not None
        assert result.name == "erk-managed-wt-02"
