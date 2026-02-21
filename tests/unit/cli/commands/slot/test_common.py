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
    is_placeholder_branch,
    is_slot_initialized,
    sync_pool_assignments,
)
from erk.cli.config import LoadedConfig
from erk.core.context import context_for_test
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    SlotInfo,
    load_pool_state,
    save_pool_state,
)
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit


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
            slot_name="erk-slot-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-slot-01"),
        )
        state = PoolState.test(assignments=(assignment,))

        result = find_oldest_assignment(state)

        assert result == assignment

    def test_returns_oldest_by_timestamp(self) -> None:
        """Returns assignment with earliest assigned_at timestamp."""
        oldest = SlotAssignment(
            slot_name="erk-slot-01",
            branch_name="feature-old",
            assigned_at="2024-01-01T10:00:00+00:00",
            worktree_path=Path("/worktrees/erk-slot-01"),
        )
        middle = SlotAssignment(
            slot_name="erk-slot-02",
            branch_name="feature-mid",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-slot-02"),
        )
        newest = SlotAssignment(
            slot_name="erk-slot-03",
            branch_name="feature-new",
            assigned_at="2024-01-01T14:00:00+00:00",
            worktree_path=Path("/worktrees/erk-slot-03"),
        )
        # Assignments in non-chronological order to test sorting
        state = PoolState.test(assignments=(newest, oldest, middle))

        result = find_oldest_assignment(state)

        assert result == oldest
        assert result.branch_name == "feature-old"


class TestFindInactiveSlot:
    """Tests for find_inactive_slot function."""

    def test_returns_none_when_no_worktrees_exist(self, tmp_path: Path) -> None:
        """Returns None when no worktrees exist in git."""
        repo_root = tmp_path / "repo"
        state = PoolState.test()
        git = FakeGit(worktrees={repo_root: []})

        result = find_inactive_slot(state, git, repo_root)

        assert result is None

    def test_returns_inactive_slot_when_available(self, tmp_path: Path) -> None:
        """Returns an unassigned slot when worktrees exist."""
        repo_root = tmp_path / "repo"
        wt1_path = tmp_path / "worktrees" / "erk-slot-01"
        wt2_path = tmp_path / "worktrees" / "erk-slot-02"
        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=wt1_path, branch="feature-a"),
                    WorktreeInfo(path=wt2_path, branch="feature-b"),
                ]
            }
        )
        state = PoolState.test(pool_size=4)

        result = find_inactive_slot(state, git, repo_root)

        assert result is not None
        slot_name, worktree_path = result
        assert slot_name == "erk-slot-01"
        assert worktree_path == wt1_path

    def test_returns_none_when_all_slots_assigned(self, tmp_path: Path) -> None:
        """Returns None when all worktrees have assignments."""
        repo_root = tmp_path / "repo"
        wt1_path = tmp_path / "worktrees" / "erk-slot-01"
        wt2_path = tmp_path / "worktrees" / "erk-slot-02"
        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=wt1_path, branch="feature-a"),
                    WorktreeInfo(path=wt2_path, branch="feature-b"),
                ]
            }
        )
        assignment1 = SlotAssignment(
            slot_name="erk-slot-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=wt1_path,
        )
        assignment2 = SlotAssignment(
            slot_name="erk-slot-02",
            branch_name="feature-b",
            assigned_at="2024-01-01T13:00:00+00:00",
            worktree_path=wt2_path,
        )
        state = PoolState.test(pool_size=2, assignments=(assignment1, assignment2))

        result = find_inactive_slot(state, git, repo_root)

        assert result is None

    def test_returns_first_inactive_slot_by_number(self, tmp_path: Path) -> None:
        """Returns the lowest-numbered unassigned slot."""
        repo_root = tmp_path / "repo"
        wt1_path = tmp_path / "worktrees" / "erk-slot-01"
        wt2_path = tmp_path / "worktrees" / "erk-slot-02"
        wt3_path = tmp_path / "worktrees" / "erk-slot-03"
        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=wt1_path, branch="feature-a"),
                    WorktreeInfo(path=wt2_path, branch="feature-b"),
                    WorktreeInfo(path=wt3_path, branch="feature-c"),
                ]
            }
        )
        assignment1 = SlotAssignment(
            slot_name="erk-slot-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=wt1_path,
        )
        state = PoolState.test(pool_size=4, assignments=(assignment1,))

        result = find_inactive_slot(state, git, repo_root)

        assert result is not None
        slot_name, worktree_path = result
        assert slot_name == "erk-slot-02"
        assert worktree_path == wt2_path

    def test_finds_orphaned_worktree_not_in_state(self, tmp_path: Path) -> None:
        """Returns slot when worktree exists in git but not tracked in state.slots.

        This is the key bug fix test: orphaned worktrees that exist
        (git knows about them) but aren't in pool.json state.slots
        should still be discovered and made available for reuse.
        """
        repo_root = tmp_path / "repo"
        wt1_path = tmp_path / "worktrees" / "erk-slot-01"
        # Git knows about this worktree
        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=wt1_path, branch="some-branch"),
                ]
            }
        )
        # But state.slots is empty (worktree not tracked in pool.json)
        state = PoolState.test(pool_size=4, slots=())

        result = find_inactive_slot(state, git, repo_root)

        # Should still find it via git
        assert result is not None
        slot_name, worktree_path = result
        assert slot_name == "erk-slot-01"
        assert worktree_path == wt1_path

    def test_ignores_non_managed_worktrees(self, tmp_path: Path) -> None:
        """Ignores worktrees that don't match erk-slot-XX pattern."""
        repo_root = tmp_path / "repo"
        root_wt = tmp_path / "repo"
        other_wt = tmp_path / "other-worktree"
        managed_wt = tmp_path / "worktrees" / "erk-slot-01"
        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=root_wt, branch="main", is_root=True),
                    WorktreeInfo(path=other_wt, branch="feature"),
                    WorktreeInfo(path=managed_wt, branch="assigned-branch"),
                ]
            }
        )
        # The managed slot is assigned
        assignment = SlotAssignment(
            slot_name="erk-slot-01",
            branch_name="assigned-branch",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=managed_wt,
        )
        state = PoolState.test(pool_size=4, assignments=(assignment,))

        result = find_inactive_slot(state, git, repo_root)

        # No managed slots available (the only managed one is assigned)
        assert result is None

    def test_respects_pool_size_limit(self, tmp_path: Path) -> None:
        """Ignores worktrees beyond pool_size."""
        repo_root = tmp_path / "repo"
        wt5_path = tmp_path / "worktrees" / "erk-slot-05"
        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=wt5_path, branch="feature"),
                ]
            }
        )
        # pool_size is 4, so slot 5 is beyond the limit
        state = PoolState.test(pool_size=4)

        result = find_inactive_slot(state, git, repo_root)

        assert result is None

    def test_skips_slot_with_uncommitted_changes(self, tmp_path: Path) -> None:
        """Skips slots with uncommitted changes, returns next clean slot."""
        repo_root = tmp_path / "repo"
        wt1_path = tmp_path / "worktrees" / "erk-slot-01"
        wt2_path = tmp_path / "worktrees" / "erk-slot-02"
        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=wt1_path, branch="feature-a"),
                    WorktreeInfo(path=wt2_path, branch="feature-b"),
                ]
            },
            # Slot 1 has uncommitted changes
            file_statuses={wt1_path: ([], ["dirty.py"], [])},
        )
        state = PoolState.test(pool_size=4)

        result = find_inactive_slot(state, git, repo_root)

        # Should skip dirty slot 1 and return clean slot 2
        assert result is not None
        slot_name, worktree_path = result
        assert slot_name == "erk-slot-02"
        assert worktree_path == wt2_path

    def test_returns_none_when_all_slots_dirty(self, tmp_path: Path) -> None:
        """Returns None when all available slots have uncommitted changes."""
        repo_root = tmp_path / "repo"
        wt1_path = tmp_path / "worktrees" / "erk-slot-01"
        git = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=wt1_path, branch="feature-a"),
                ]
            },
            file_statuses={wt1_path: ([], ["dirty.py"], [])},
        )
        state = PoolState.test(pool_size=4)

        result = find_inactive_slot(state, git, repo_root)

        assert result is None


class TestIsSlotInitialized:
    """Tests for is_slot_initialized function."""

    def test_returns_false_when_no_slots(self) -> None:
        """Returns False when no slots are initialized."""
        state = PoolState.test()

        assert is_slot_initialized(state, "erk-slot-01") is False

    def test_returns_true_when_slot_exists(self) -> None:
        """Returns True when the slot is in the initialized list."""
        slot = SlotInfo(name="erk-slot-01")
        state = PoolState.test(slots=(slot,))

        assert is_slot_initialized(state, "erk-slot-01") is True

    def test_returns_false_for_different_slot(self) -> None:
        """Returns False when checking for a slot not in the list."""
        slot = SlotInfo(name="erk-slot-01")
        state = PoolState.test(slots=(slot,))

        assert is_slot_initialized(state, "erk-slot-02") is False


class TestFindNextAvailableSlot:
    """Tests for find_next_available_slot function."""

    def test_returns_first_slot_when_empty(self) -> None:
        """Returns slot 1 when no slots exist and no assignments."""
        state = PoolState.test(pool_size=4)

        result = find_next_available_slot(state, None)

        assert result == 1

    def test_returns_none_when_pool_full_with_assignments(self) -> None:
        """Returns None when all slots are assigned."""
        assignment1 = SlotAssignment(
            slot_name="erk-slot-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-slot-01"),
        )
        assignment2 = SlotAssignment(
            slot_name="erk-slot-02",
            branch_name="feature-b",
            assigned_at="2024-01-01T13:00:00+00:00",
            worktree_path=Path("/worktrees/erk-slot-02"),
        )
        state = PoolState.test(pool_size=2, assignments=(assignment1, assignment2))

        result = find_next_available_slot(state, None)

        assert result is None

    def test_skips_assigned_slot(self) -> None:
        """Returns next available slot, skipping assigned ones."""
        assignment = SlotAssignment(
            slot_name="erk-slot-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-slot-01"),
        )
        state = PoolState.test(pool_size=4, assignments=(assignment,))

        result = find_next_available_slot(state, None)

        assert result == 2

    def test_skips_initialized_slot_without_assignment(self) -> None:
        """Returns slot that is neither assigned nor initialized.

        This is the key bug fix test: when a slot exists on disk
        (in state.slots) but is not assigned (not in state.assignments),
        find_next_available_slot should NOT return that slot number.
        """
        # Slot 1 exists on disk but has no assignment
        slot1 = SlotInfo(name="erk-slot-01")
        state = PoolState.test(pool_size=4, slots=(slot1,))

        result = find_next_available_slot(state, None)

        # Should return 2, not 1 (since 1 already exists on disk)
        assert result == 2

    def test_skips_both_assigned_and_initialized_slots(self) -> None:
        """Returns first slot that is neither assigned nor initialized."""
        # Slot 1: initialized but not assigned
        slot1 = SlotInfo(name="erk-slot-01")
        # Slot 2: initialized AND assigned
        slot2 = SlotInfo(name="erk-slot-02")
        assignment2 = SlotAssignment(
            slot_name="erk-slot-02",
            branch_name="feature-b",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=Path("/worktrees/erk-slot-02"),
        )
        state = PoolState.test(pool_size=4, slots=(slot1, slot2), assignments=(assignment2,))

        result = find_next_available_slot(state, None)

        # Should return 3, skipping both 1 (initialized) and 2 (assigned)
        assert result == 3

    def test_returns_none_when_all_slots_initialized(self) -> None:
        """Returns None when all slots are initialized (even without assignments)."""
        slot1 = SlotInfo(name="erk-slot-01")
        slot2 = SlotInfo(name="erk-slot-02")
        state = PoolState.test(pool_size=2, slots=(slot1, slot2))

        result = find_next_available_slot(state, None)

        assert result is None

    def test_skips_slot_with_orphaned_directory_on_disk(self, tmp_path: Path) -> None:
        """Skips slot when directory exists on disk but not tracked in state.

        This tests the bug fix for orphaned worktree directories that exist
        on disk but aren't tracked in pool.json. Without this check, trying
        to create a worktree in such a slot fails with:
        'fatal: <path> already exists'
        """
        # Create orphaned directory for slot 1
        worktrees_dir = tmp_path / "worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "erk-slot-01").mkdir()

        # State has no knowledge of slot 1
        state = PoolState.test(pool_size=4)

        result = find_next_available_slot(state, worktrees_dir)

        # Should return 2, not 1 (since directory exists on disk)
        assert result == 2

    def test_skips_multiple_orphaned_directories(self, tmp_path: Path) -> None:
        """Skips multiple orphaned directories."""
        worktrees_dir = tmp_path / "worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "erk-slot-01").mkdir()
        (worktrees_dir / "erk-slot-02").mkdir()

        state = PoolState.test(pool_size=4)

        result = find_next_available_slot(state, worktrees_dir)

        # Should return 3, skipping both orphaned directories
        assert result == 3

    def test_returns_none_when_all_slots_have_orphaned_directories(self, tmp_path: Path) -> None:
        """Returns None when all slots have orphaned directories."""
        worktrees_dir = tmp_path / "worktrees"
        worktrees_dir.mkdir()
        (worktrees_dir / "erk-slot-01").mkdir()
        (worktrees_dir / "erk-slot-02").mkdir()

        state = PoolState.test(pool_size=2)

        result = find_next_available_slot(state, worktrees_dir)

        assert result is None


def test_extract_slot_number_valid() -> None:
    """Extracts slot number from valid slot name."""
    assert extract_slot_number("erk-slot-01") == "01"
    assert extract_slot_number("erk-slot-03") == "03"
    assert extract_slot_number("erk-slot-99") == "99"


def test_extract_slot_number_invalid() -> None:
    """Returns None for invalid slot names."""
    assert extract_slot_number("invalid-name") is None
    assert extract_slot_number("erk-slot-1") is None  # Single digit
    assert extract_slot_number("erk-slot-001") is None  # Three digits
    assert extract_slot_number("erk-slot-ab") is None  # Non-numeric
    assert extract_slot_number("") is None


def test_get_placeholder_branch_name_valid() -> None:
    """Returns correct placeholder branch name for valid slot."""
    assert get_placeholder_branch_name("erk-slot-01") == "__erk-slot-01-br-stub__"
    assert get_placeholder_branch_name("erk-slot-03") == "__erk-slot-03-br-stub__"
    assert get_placeholder_branch_name("erk-slot-99") == "__erk-slot-99-br-stub__"


def test_get_placeholder_branch_name_invalid() -> None:
    """Returns None for invalid slot names."""
    assert get_placeholder_branch_name("invalid-name") is None
    assert get_placeholder_branch_name("erk-slot-1") is None


def test_is_placeholder_branch_valid() -> None:
    """Returns True for valid placeholder branch names."""
    assert is_placeholder_branch("__erk-slot-01-br-stub__") is True
    assert is_placeholder_branch("__erk-slot-02-br-stub__") is True
    assert is_placeholder_branch("__erk-slot-99-br-stub__") is True


def test_is_placeholder_branch_invalid() -> None:
    """Returns False for non-placeholder branch names."""
    assert is_placeholder_branch("main") is False
    assert is_placeholder_branch("master") is False
    assert is_placeholder_branch("feature/my-branch") is False
    # Missing underscores
    assert is_placeholder_branch("erk-slot-01-placeholder") is False
    # Wrong prefix
    assert is_placeholder_branch("__erk-slot-01__") is False
    # Missing suffix
    assert is_placeholder_branch("__erk-slot-01__") is False
    # Extra content
    assert is_placeholder_branch("__erk-slot-01-br-stub__-extra") is False
    # Non-numeric slot
    assert is_placeholder_branch("__erk-slot-xx-br-stub__") is False


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
        slot_path = tmp_path / "worktrees" / "erk-slot-01"
        other_path = tmp_path / "other" / "location"
        assignment = SlotAssignment(
            slot_name="erk-slot-01",
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
        slot_path = tmp_path / "worktrees" / "erk-slot-01"
        assignment = SlotAssignment(
            slot_name="erk-slot-01",
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
        slot_path = tmp_path / "worktrees" / "erk-slot-01"
        subdir = slot_path / "src" / "nested"
        assignment = SlotAssignment(
            slot_name="erk-slot-01",
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
        slot1_path = tmp_path / "worktrees" / "erk-slot-01"
        slot2_path = tmp_path / "worktrees" / "erk-slot-02"
        assignment1 = SlotAssignment(
            slot_name="erk-slot-01",
            branch_name="feature-a",
            assigned_at="2024-01-01T12:00:00+00:00",
            worktree_path=slot1_path,
        )
        assignment2 = SlotAssignment(
            slot_name="erk-slot-02",
            branch_name="feature-b",
            assigned_at="2024-01-01T13:00:00+00:00",
            worktree_path=slot2_path,
        )
        state = PoolState.test(assignments=(assignment1, assignment2))
        # Git reports slot2_path as the worktree root
        git = FakeGit(repository_roots={slot2_path: slot2_path})

        result = find_assignment_by_worktree(state, git, slot2_path)

        assert result == assignment2
        assert result.slot_name == "erk-slot-02"


def test_sync_no_changes_when_branches_match(tmp_path: Path) -> None:
    """Returns same state and synced_count=0 when all branches match."""
    wt_path = tmp_path / "worktrees" / "erk-slot-01"
    wt_path.mkdir(parents=True)
    assignment = SlotAssignment(
        slot_name="erk-slot-01",
        branch_name="feature-a",
        assigned_at="2024-01-01T12:00:00+00:00",
        worktree_path=wt_path,
    )
    state = PoolState.test(assignments=(assignment,))
    git = FakeGit(current_branches={wt_path: "feature-a"})
    pool_json = tmp_path / "pool.json"

    result = sync_pool_assignments(state, git, pool_json)

    assert result.synced_count == 0
    assert result.state is state


def test_sync_updates_when_branch_changed(tmp_path: Path) -> None:
    """Updates branch_name and preserves assigned_at when branch changed."""
    wt_path = tmp_path / "worktrees" / "erk-slot-01"
    wt_path.mkdir(parents=True)
    assignment = SlotAssignment(
        slot_name="erk-slot-01",
        branch_name="feature-a",
        assigned_at="2024-01-01T12:00:00+00:00",
        worktree_path=wt_path,
    )
    state = PoolState.test(assignments=(assignment,))
    git = FakeGit(current_branches={wt_path: "feature-b"})
    pool_json = tmp_path / "pool.json"

    result = sync_pool_assignments(state, git, pool_json)

    assert result.synced_count == 1
    assert len(result.state.assignments) == 1
    synced = result.state.assignments[0]
    assert synced.branch_name == "feature-b"
    assert synced.assigned_at == "2024-01-01T12:00:00+00:00"
    assert synced.slot_name == "erk-slot-01"
    assert synced.worktree_path == wt_path


def test_sync_saves_to_disk_on_change(tmp_path: Path) -> None:
    """pool.json is updated on disk after sync detects a change."""
    wt_path = tmp_path / "worktrees" / "erk-slot-01"
    wt_path.mkdir(parents=True)
    assignment = SlotAssignment(
        slot_name="erk-slot-01",
        branch_name="feature-a",
        assigned_at="2024-01-01T12:00:00+00:00",
        worktree_path=wt_path,
    )
    state = PoolState.test(assignments=(assignment,))
    git = FakeGit(current_branches={wt_path: "feature-b"})
    pool_json = tmp_path / "pool.json"

    sync_pool_assignments(state, git, pool_json)

    loaded = load_pool_state(pool_json)
    assert loaded is not None
    assert loaded.assignments[0].branch_name == "feature-b"


def test_sync_does_not_save_when_unchanged(tmp_path: Path) -> None:
    """pool.json mtime is unchanged when no sync needed."""
    wt_path = tmp_path / "worktrees" / "erk-slot-01"
    wt_path.mkdir(parents=True)
    assignment = SlotAssignment(
        slot_name="erk-slot-01",
        branch_name="feature-a",
        assigned_at="2024-01-01T12:00:00+00:00",
        worktree_path=wt_path,
    )
    state = PoolState.test(assignments=(assignment,))
    git = FakeGit(current_branches={wt_path: "feature-a"})
    pool_json = tmp_path / "pool.json"
    # Write initial state to disk
    save_pool_state(pool_json, state)
    mtime_before = pool_json.stat().st_mtime

    sync_pool_assignments(state, git, pool_json)

    mtime_after = pool_json.stat().st_mtime
    assert mtime_before == mtime_after


def test_sync_skips_missing_worktree_path(tmp_path: Path) -> None:
    """Non-existent worktree paths are left unchanged."""
    missing_path = tmp_path / "worktrees" / "erk-slot-01"  # Not created
    assignment = SlotAssignment(
        slot_name="erk-slot-01",
        branch_name="feature-a",
        assigned_at="2024-01-01T12:00:00+00:00",
        worktree_path=missing_path,
    )
    state = PoolState.test(assignments=(assignment,))
    git = FakeGit()
    pool_json = tmp_path / "pool.json"

    result = sync_pool_assignments(state, git, pool_json)

    assert result.synced_count == 0
    assert result.state.assignments[0].branch_name == "feature-a"


def test_sync_skips_detached_head(tmp_path: Path) -> None:
    """Detached HEAD (None branch) leaves assignment unchanged."""
    wt_path = tmp_path / "worktrees" / "erk-slot-01"
    wt_path.mkdir(parents=True)
    assignment = SlotAssignment(
        slot_name="erk-slot-01",
        branch_name="feature-a",
        assigned_at="2024-01-01T12:00:00+00:00",
        worktree_path=wt_path,
    )
    state = PoolState.test(assignments=(assignment,))
    # None indicates detached HEAD
    git = FakeGit(current_branches={wt_path: None})
    pool_json = tmp_path / "pool.json"

    result = sync_pool_assignments(state, git, pool_json)

    assert result.synced_count == 0
    assert result.state.assignments[0].branch_name == "feature-a"


def test_sync_skips_placeholder_branch(tmp_path: Path) -> None:
    """Placeholder branches are left unchanged."""
    wt_path = tmp_path / "worktrees" / "erk-slot-01"
    wt_path.mkdir(parents=True)
    assignment = SlotAssignment(
        slot_name="erk-slot-01",
        branch_name="feature-a",
        assigned_at="2024-01-01T12:00:00+00:00",
        worktree_path=wt_path,
    )
    state = PoolState.test(assignments=(assignment,))
    git = FakeGit(current_branches={wt_path: "__erk-slot-01-br-stub__"})
    pool_json = tmp_path / "pool.json"

    result = sync_pool_assignments(state, git, pool_json)

    assert result.synced_count == 0
    assert result.state.assignments[0].branch_name == "feature-a"


def test_sync_multiple_assignments(tmp_path: Path) -> None:
    """Syncs changed assignments while preserving unchanged ones."""
    wt1_path = tmp_path / "worktrees" / "erk-slot-01"
    wt2_path = tmp_path / "worktrees" / "erk-slot-02"
    wt3_path = tmp_path / "worktrees" / "erk-slot-03"
    wt1_path.mkdir(parents=True)
    wt2_path.mkdir(parents=True)
    wt3_path.mkdir(parents=True)
    assignment1 = SlotAssignment(
        slot_name="erk-slot-01",
        branch_name="feature-a",
        assigned_at="2024-01-01T10:00:00+00:00",
        worktree_path=wt1_path,
    )
    assignment2 = SlotAssignment(
        slot_name="erk-slot-02",
        branch_name="feature-b",
        assigned_at="2024-01-01T11:00:00+00:00",
        worktree_path=wt2_path,
    )
    assignment3 = SlotAssignment(
        slot_name="erk-slot-03",
        branch_name="feature-c",
        assigned_at="2024-01-01T12:00:00+00:00",
        worktree_path=wt3_path,
    )
    state = PoolState.test(assignments=(assignment1, assignment2, assignment3))
    git = FakeGit(
        current_branches={
            wt1_path: "feature-a",  # unchanged
            wt2_path: "feature-b-new",  # changed
            wt3_path: "feature-c",  # unchanged
        }
    )
    pool_json = tmp_path / "pool.json"

    result = sync_pool_assignments(state, git, pool_json)

    assert result.synced_count == 1
    assert result.state.assignments[0].branch_name == "feature-a"
    assert result.state.assignments[1].branch_name == "feature-b-new"
    assert result.state.assignments[1].assigned_at == "2024-01-01T11:00:00+00:00"
    assert result.state.assignments[2].branch_name == "feature-c"


def test_eviction_uses_synced_state(tmp_path: Path) -> None:
    """End-to-end: sync + find_inactive_slot avoids evicting active slot.

    Scenario: slot-01 is assigned to feature-a in pool.json, but the user
    manually checked out feature-x. Without sync, find_inactive_slot would
    see slot-01 as assigned to feature-a and not evict it even though
    feature-a no longer occupies it. With sync, the assignment updates to
    feature-x, and the eviction logic operates on accurate state.
    """
    repo_root = tmp_path / "repo"
    wt1_path = tmp_path / "worktrees" / "erk-slot-01"
    wt2_path = tmp_path / "worktrees" / "erk-slot-02"
    wt1_path.mkdir(parents=True)
    wt2_path.mkdir(parents=True)
    assignment1 = SlotAssignment(
        slot_name="erk-slot-01",
        branch_name="feature-a",
        assigned_at="2024-01-01T10:00:00+00:00",
        worktree_path=wt1_path,
    )
    assignment2 = SlotAssignment(
        slot_name="erk-slot-02",
        branch_name="feature-b",
        assigned_at="2024-01-01T11:00:00+00:00",
        worktree_path=wt2_path,
    )
    state = PoolState.test(pool_size=2, assignments=(assignment1, assignment2))
    # User manually changed slot-01 from feature-a to feature-x
    git = FakeGit(
        current_branches={
            wt1_path: "feature-x",
            wt2_path: "feature-b",
        },
        worktrees={
            repo_root: [
                WorktreeInfo(path=wt1_path, branch="feature-x"),
                WorktreeInfo(path=wt2_path, branch="feature-b"),
            ]
        },
    )
    pool_json = tmp_path / "pool.json"

    # First sync to get accurate state
    sync_result = sync_pool_assignments(state, git, pool_json)

    # Verify sync updated slot-01's branch
    assert sync_result.state.assignments[0].branch_name == "feature-x"

    # Now find_inactive_slot operates on accurate state — both slots are
    # assigned so none should be available for eviction
    inactive = find_inactive_slot(sync_result.state, git, repo_root)
    assert inactive is None
