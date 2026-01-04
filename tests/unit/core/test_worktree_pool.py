"""Unit tests for worktree pool state management."""

from pathlib import Path

from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    SlotInfo,
    load_pool_state,
    save_pool_state,
)


def test_slot_assignment_creation() -> None:
    """Test that SlotAssignment is created correctly."""
    assignment = SlotAssignment(
        slot_name="erk-managed-wt-01",
        branch_name="feature-xyz",
        assigned_at="2025-01-03T10:30:00+00:00",
        worktree_path=Path("/path/to/worktree"),
    )

    assert assignment.slot_name == "erk-managed-wt-01"
    assert assignment.branch_name == "feature-xyz"
    assert assignment.assigned_at == "2025-01-03T10:30:00+00:00"
    assert assignment.worktree_path == Path("/path/to/worktree")


def test_pool_state_creation() -> None:
    """Test that PoolState is created correctly."""
    assignment = SlotAssignment(
        slot_name="erk-managed-wt-01",
        branch_name="feature-xyz",
        assigned_at="2025-01-03T10:30:00+00:00",
        worktree_path=Path("/path/to/worktree"),
    )

    state = PoolState(
        version="1.0",
        pool_size=4,
        assignments=(assignment,),
        slots=(),
    )

    assert state.version == "1.0"
    assert state.pool_size == 4
    assert len(state.assignments) == 1
    assert state.assignments[0] == assignment
    assert len(state.slots) == 0


def test_pool_state_empty_assignments() -> None:
    """Test that PoolState works with no assignments."""
    state = PoolState(
        version="1.0",
        pool_size=4,
        assignments=(),
        slots=(),
    )

    assert state.version == "1.0"
    assert state.pool_size == 4
    assert len(state.assignments) == 0
    assert len(state.slots) == 0


def test_load_pool_state_nonexistent_file(tmp_path: Path) -> None:
    """Test that load_pool_state returns None for nonexistent file."""
    pool_json = tmp_path / "pool.json"

    result = load_pool_state(pool_json)

    assert result is None


def test_save_and_load_pool_state_empty(tmp_path: Path) -> None:
    """Test round-trip save and load with empty assignments."""
    pool_json = tmp_path / "pool.json"

    state = PoolState(
        version="1.0",
        pool_size=4,
        assignments=(),
        slots=(),
    )

    save_pool_state(pool_json, state)
    loaded = load_pool_state(pool_json)

    assert loaded is not None
    assert loaded.version == "1.0"
    assert loaded.pool_size == 4
    assert len(loaded.assignments) == 0
    assert len(loaded.slots) == 0


def test_save_and_load_pool_state_with_assignments(tmp_path: Path) -> None:
    """Test round-trip save and load with assignments."""
    pool_json = tmp_path / "pool.json"

    assignment1 = SlotAssignment(
        slot_name="erk-managed-wt-01",
        branch_name="feature-a",
        assigned_at="2025-01-03T10:30:00+00:00",
        worktree_path=Path("/path/to/wt1"),
    )
    assignment2 = SlotAssignment(
        slot_name="erk-managed-wt-02",
        branch_name="feature-b",
        assigned_at="2025-01-03T11:00:00+00:00",
        worktree_path=Path("/path/to/wt2"),
    )

    state = PoolState(
        version="1.0",
        pool_size=4,
        assignments=(assignment1, assignment2),
        slots=(),
    )

    save_pool_state(pool_json, state)
    loaded = load_pool_state(pool_json)

    assert loaded is not None
    assert loaded.version == "1.0"
    assert loaded.pool_size == 4
    assert len(loaded.assignments) == 2
    assert loaded.assignments[0].slot_name == "erk-managed-wt-01"
    assert loaded.assignments[0].branch_name == "feature-a"
    assert loaded.assignments[1].slot_name == "erk-managed-wt-02"
    assert loaded.assignments[1].branch_name == "feature-b"


def test_save_pool_state_creates_parent_dirs(tmp_path: Path) -> None:
    """Test that save_pool_state creates parent directories."""
    pool_json = tmp_path / "nested" / "dir" / "pool.json"

    state = PoolState(
        version="1.0",
        pool_size=4,
        assignments=(),
        slots=(),
    )

    save_pool_state(pool_json, state)

    assert pool_json.exists()
    loaded = load_pool_state(pool_json)
    assert loaded is not None
    assert loaded.pool_size == 4


def test_slot_info_creation() -> None:
    """Test that SlotInfo is created correctly."""
    slot = SlotInfo(name="erk-managed-wt-01")

    assert slot.name == "erk-managed-wt-01"


def test_pool_state_with_slots() -> None:
    """Test that PoolState works with slots."""
    slot1 = SlotInfo(name="erk-managed-wt-01")
    slot2 = SlotInfo(name="erk-managed-wt-02")

    state = PoolState(
        version="1.0",
        pool_size=4,
        assignments=(),
        slots=(slot1, slot2),
    )

    assert len(state.slots) == 2
    assert state.slots[0].name == "erk-managed-wt-01"
    assert state.slots[1].name == "erk-managed-wt-02"


def test_save_and_load_pool_state_with_slots(tmp_path: Path) -> None:
    """Test round-trip save and load with slots."""
    pool_json = tmp_path / "pool.json"

    slot1 = SlotInfo(name="erk-managed-wt-01")
    slot2 = SlotInfo(name="erk-managed-wt-02")

    state = PoolState(
        version="1.0",
        pool_size=4,
        assignments=(),
        slots=(slot1, slot2),
    )

    save_pool_state(pool_json, state)
    loaded = load_pool_state(pool_json)

    assert loaded is not None
    assert len(loaded.slots) == 2
    assert loaded.slots[0].name == "erk-managed-wt-01"
    assert loaded.slots[1].name == "erk-managed-wt-02"
