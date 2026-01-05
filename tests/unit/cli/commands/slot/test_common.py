"""Unit tests for slot common module utilities."""

from pathlib import Path

from erk.cli.commands.slot.common import (
    DEFAULT_POOL_SIZE,
    extract_slot_number,
    find_assignment_by_worktree,
    find_inactive_slot,
    find_next_available_slot,
    find_oldest_assignment,
    get_placeholder_branch_name,
    get_pool_size,
    is_slot_initialized,
)
from erk.cli.config import LoadedConfig
from erk.core.context import context_for_test
from erk.core.worktree_pool import PoolState, SlotAssignment, SlotInfo
from erk_shared.git.fake import FakeGit


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
        state = PoolState.test()

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
        state = PoolState.test(assignments=(assignment,))

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
        state = PoolState.test(assignments=(newest, oldest, middle))

        result = find_oldest_assignment(state)

        assert result == oldest
        assert result.branch_name == "feature-old"


class TestFindInactiveSlot:
    """Tests for find_inactive_slot function."""

    def test_returns_none_when_no_slots_initialized(self) -> None:
        """Returns None when no slots are initialized."""
        state = PoolState.test()

        result = find_inactive_slot(state)

        assert result is None

    def test_returns_inactive_slot_when_available(self) -> None:
        """Returns an inactive slot when available."""
        slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
        slot2 = SlotInfo(name="erk-managed-wt-02", last_objective_issue=None)
        state = PoolState.test(slots=(slot1, slot2))

        result = find_inactive_slot(state)

        assert result is not None
        assert result.name == "erk-managed-wt-01"

    def test_returns_none_when_all_slots_assigned(self) -> None:
        """Returns None when all initialized slots have assignments."""
        slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
        slot2 = SlotInfo(name="erk-managed-wt-02", last_objective_issue=None)
        assignment1 = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-01"),
        )
        assignment2 = SlotAssignment(
            slot_name="erk-managed-wt-02",
            branch_name="feature-b",
            assigned_at="2024-01-01T13:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-02"),
        )
        state = PoolState.test(slots=(slot1, slot2), assignments=(assignment1, assignment2))

        result = find_inactive_slot(state)

        assert result is None

    def test_returns_first_inactive_slot(self) -> None:
        """Returns the first slot that is not assigned."""
        slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
        slot2 = SlotInfo(name="erk-managed-wt-02", last_objective_issue=None)
        slot3 = SlotInfo(name="erk-managed-wt-03", last_objective_issue=None)
        assignment1 = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-01"),
        )
        state = PoolState.test(slots=(slot1, slot2, slot3), assignments=(assignment1,))

        result = find_inactive_slot(state)

        assert result is not None
        assert result.name == "erk-managed-wt-02"


class TestIsSlotInitialized:
    """Tests for is_slot_initialized function."""

    def test_returns_false_when_no_slots(self) -> None:
        """Returns False when no slots are initialized."""
        state = PoolState.test()

        assert is_slot_initialized(state, "erk-managed-wt-01") is False

    def test_returns_true_when_slot_exists(self) -> None:
        """Returns True when the slot is in the initialized list."""
        slot = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
        state = PoolState.test(slots=(slot,))

        assert is_slot_initialized(state, "erk-managed-wt-01") is True

    def test_returns_false_for_different_slot(self) -> None:
        """Returns False when checking for a slot not in the list."""
        slot = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
        state = PoolState.test(slots=(slot,))

        assert is_slot_initialized(state, "erk-managed-wt-02") is False


class TestFindNextAvailableSlot:
    """Tests for find_next_available_slot function."""

    def test_returns_first_slot_when_empty(self) -> None:
        """Returns slot 1 when no slots exist and no assignments."""
        state = PoolState.test(pool_size=4)

        result = find_next_available_slot(state)

        assert result == 1

    def test_returns_none_when_pool_full_with_assignments(self) -> None:
        """Returns None when all slots are assigned."""
        assignment1 = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-01"),
        )
        assignment2 = SlotAssignment(
            slot_name="erk-managed-wt-02",
            branch_name="feature-b",
            assigned_at="2024-01-01T13:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-02"),
        )
        state = PoolState.test(pool_size=2, assignments=(assignment1, assignment2))

        result = find_next_available_slot(state)

        assert result is None

    def test_skips_assigned_slot(self) -> None:
        """Returns next available slot, skipping assigned ones."""
        assignment = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-01"),
        )
        state = PoolState.test(pool_size=4, assignments=(assignment,))

        result = find_next_available_slot(state)

        assert result == 2

    def test_skips_initialized_slot_without_assignment(self) -> None:
        """Returns slot that is neither assigned nor initialized.

        This is the key bug fix test: when a slot exists on disk
        (in state.slots) but is not assigned (not in state.assignments),
        find_next_available_slot should NOT return that slot number.
        """
        # Slot 1 exists on disk but has no assignment
        slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
        state = PoolState.test(pool_size=4, slots=(slot1,))

        result = find_next_available_slot(state)

        # Should return 2, not 1 (since 1 already exists on disk)
        assert result == 2

    def test_skips_both_assigned_and_initialized_slots(self) -> None:
        """Returns first slot that is neither assigned nor initialized."""
        # Slot 1: initialized but not assigned
        slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
        # Slot 2: initialized AND assigned
        slot2 = SlotInfo(name="erk-managed-wt-02", last_objective_issue=None)
        assignment2 = SlotAssignment(
            slot_name="erk-managed-wt-02",
            branch_name="feature-b",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-managed-wt-02"),
        )
        state = PoolState.test(pool_size=4, slots=(slot1, slot2), assignments=(assignment2,))

        result = find_next_available_slot(state)

        # Should return 3, skipping both 1 (initialized) and 2 (assigned)
        assert result == 3

    def test_returns_none_when_all_slots_initialized(self) -> None:
        """Returns None when all slots are initialized (even without assignments)."""
        slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
        slot2 = SlotInfo(name="erk-managed-wt-02", last_objective_issue=None)
        state = PoolState.test(pool_size=2, slots=(slot1, slot2))

        result = find_next_available_slot(state)

        assert result is None


def test_extract_slot_number_valid() -> None:
    """Extracts slot number from valid slot name."""
    assert extract_slot_number("erk-managed-wt-01") == "01"
    assert extract_slot_number("erk-managed-wt-03") == "03"
    assert extract_slot_number("erk-managed-wt-99") == "99"


def test_extract_slot_number_invalid() -> None:
    """Returns None for invalid slot names."""
    assert extract_slot_number("invalid-name") is None
    assert extract_slot_number("erk-managed-wt-1") is None  # Single digit
    assert extract_slot_number("erk-managed-wt-001") is None  # Three digits
    assert extract_slot_number("erk-managed-wt-ab") is None  # Non-numeric
    assert extract_slot_number("") is None


def test_get_placeholder_branch_name_valid() -> None:
    """Returns correct placeholder branch name for valid slot."""
    assert get_placeholder_branch_name("erk-managed-wt-01") == "__erk-slot-01-placeholder__"
    assert get_placeholder_branch_name("erk-managed-wt-03") == "__erk-slot-03-placeholder__"
    assert get_placeholder_branch_name("erk-managed-wt-99") == "__erk-slot-99-placeholder__"


def test_get_placeholder_branch_name_invalid() -> None:
    """Returns None for invalid slot names."""
    assert get_placeholder_branch_name("invalid-name") is None
    assert get_placeholder_branch_name("erk-managed-wt-1") is None


class TestFindAssignmentByWorktree:
    """Tests for find_assignment_by_worktree function."""

    def test_returns_none_for_empty_state(self, tmp_path: Path) -> None:
        """Returns None when no assignments exist."""
        state = PoolState.test()
        cwd = tmp_path / "somewhere"
        git = FakeGit(repository_roots={cwd: cwd})

        result = find_assignment_by_worktree(state, git, cwd)

        assert result is None

    def test_returns_none_when_cwd_not_in_any_slot(self, tmp_path: Path) -> None:
        """Returns None when cwd is not within any assigned slot."""
        slot_path = tmp_path / "worktrees" / "erk-managed-wt-01"
        other_path = tmp_path / "other" / "location"
        assignment = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=slot_path,
        )
        state = PoolState.test(assignments=(assignment,))
        # Git reports other_path as its own worktree root (not in a managed slot)
        git = FakeGit(repository_roots={other_path: other_path})

        result = find_assignment_by_worktree(state, git, other_path)

        assert result is None

    def test_returns_assignment_when_cwd_equals_worktree_path(self, tmp_path: Path) -> None:
        """Returns assignment when cwd exactly matches worktree path."""
        slot_path = tmp_path / "worktrees" / "erk-managed-wt-01"
        assignment = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=slot_path,
        )
        state = PoolState.test(assignments=(assignment,))
        # Git reports slot_path as the worktree root
        git = FakeGit(repository_roots={slot_path: slot_path})

        result = find_assignment_by_worktree(state, git, slot_path)

        assert result == assignment

    def test_returns_assignment_when_cwd_is_subdirectory(self, tmp_path: Path) -> None:
        """Returns assignment when cwd is a subdirectory of worktree path."""
        slot_path = tmp_path / "worktrees" / "erk-managed-wt-01"
        subdir = slot_path / "src" / "nested"
        assignment = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=slot_path,
        )
        state = PoolState.test(assignments=(assignment,))
        # Git reports slot_path as the worktree root for the subdirectory
        git = FakeGit(repository_roots={subdir: slot_path})

        result = find_assignment_by_worktree(state, git, subdir)

        assert result == assignment

    def test_returns_matching_assignment_for_slot(self, tmp_path: Path) -> None:
        """Returns matching assignment when multiple slots exist."""
        slot1_path = tmp_path / "worktrees" / "erk-managed-wt-01"
        slot2_path = tmp_path / "worktrees" / "erk-managed-wt-02"
        assignment1 = SlotAssignment(
            slot_name="erk-managed-wt-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=slot1_path,
        )
        assignment2 = SlotAssignment(
            slot_name="erk-managed-wt-02",
            branch_name="feature-b",
            assigned_at="2024-01-01T13:00:00+00:00",
            worktree_path=slot2_path,
        )
        state = PoolState.test(assignments=(assignment1, assignment2))
        # Git reports slot2_path as the worktree root
        git = FakeGit(repository_roots={slot2_path: slot2_path})

        result = find_assignment_by_worktree(state, git, slot2_path)

        assert result == assignment2
        assert result.slot_name == "erk-managed-wt-02"
