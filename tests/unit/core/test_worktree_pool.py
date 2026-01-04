"""Unit tests for worktree pool state management."""

from pathlib import Path

from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    SlotInfo,
    load_pool_state,
    save_pool_state,
    update_slot_objective,
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
        slots=(),
        assignments=(assignment,),
    )

    assert state.version == "1.0"
    assert state.pool_size == 4
    assert len(state.slots) == 0
    assert len(state.assignments) == 1
    assert state.assignments[0] == assignment


def test_pool_state_empty_assignments() -> None:
    """Test that PoolState works with no assignments."""
    state = PoolState(
        version="1.0",
        pool_size=4,
        slots=(),
        assignments=(),
    )

    assert state.version == "1.0"
    assert state.pool_size == 4
    assert len(state.slots) == 0
    assert len(state.assignments) == 0


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
        slots=(),
        assignments=(),
    )

    save_pool_state(pool_json, state)
    loaded = load_pool_state(pool_json)

    assert loaded is not None
    assert loaded.version == "1.0"
    assert loaded.pool_size == 4
    assert len(loaded.slots) == 0
    assert len(loaded.assignments) == 0


def test_save_and_load_pool_state_with_assignments(tmp_path: Path) -> None:
    """Test round-trip save and load with assignments."""
    pool_json = tmp_path / "pool.json"

    slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
    slot2 = SlotInfo(name="erk-managed-wt-02", last_objective_issue=None)

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
        slots=(slot1, slot2),
        assignments=(assignment1, assignment2),
    )

    save_pool_state(pool_json, state)
    loaded = load_pool_state(pool_json)

    assert loaded is not None
    assert loaded.version == "1.0"
    assert loaded.pool_size == 4
    assert len(loaded.slots) == 2
    assert loaded.slots[0].name == "erk-managed-wt-01"
    assert loaded.slots[1].name == "erk-managed-wt-02"
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
        slots=(),
        assignments=(),
    )

    save_pool_state(pool_json, state)

    assert pool_json.exists()
    loaded = load_pool_state(pool_json)
    assert loaded is not None
    assert loaded.pool_size == 4


def test_slot_info_creation() -> None:
    """Test that SlotInfo is created correctly."""
    slot = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)

    assert slot.name == "erk-managed-wt-01"
    assert slot.last_objective_issue is None


def test_slot_info_with_objective() -> None:
    """Test that SlotInfo preserves last_objective_issue."""
    slot = SlotInfo(name="erk-managed-wt-01", last_objective_issue=42)

    assert slot.name == "erk-managed-wt-01"
    assert slot.last_objective_issue == 42


def test_pool_state_with_slots_no_assignments() -> None:
    """Test PoolState with initialized slots but no assignments."""
    slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
    slot2 = SlotInfo(name="erk-managed-wt-02", last_objective_issue=None)

    state = PoolState(
        version="1.0",
        pool_size=4,
        slots=(slot1, slot2),
        assignments=(),
    )

    assert state.version == "1.0"
    assert state.pool_size == 4
    assert len(state.slots) == 2
    assert state.slots[0].name == "erk-managed-wt-01"
    assert state.slots[1].name == "erk-managed-wt-02"
    assert len(state.assignments) == 0


def test_save_and_load_pool_state_with_objective(tmp_path: Path) -> None:
    """Test round-trip save and load preserves last_objective_issue."""
    pool_json = tmp_path / "pool.json"

    slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=123)
    slot2 = SlotInfo(name="erk-managed-wt-02", last_objective_issue=None)

    state = PoolState(
        version="1.0",
        pool_size=4,
        slots=(slot1, slot2),
        assignments=(),
    )

    save_pool_state(pool_json, state)
    loaded = load_pool_state(pool_json)

    assert loaded is not None
    assert loaded.slots[0].last_objective_issue == 123
    assert loaded.slots[1].last_objective_issue is None


def test_load_pool_state_missing_objective_field(tmp_path: Path) -> None:
    """Test that loading old pool.json without last_objective_issue defaults to None."""
    pool_json = tmp_path / "pool.json"

    # Write old-format data without last_objective_issue field
    old_format_json = (
        '{"version": "1.0", "pool_size": 4, '
        '"slots": [{"name": "erk-managed-wt-01"}], "assignments": []}'
    )
    pool_json.write_text(old_format_json, encoding="utf-8")

    loaded = load_pool_state(pool_json)

    assert loaded is not None
    assert loaded.slots[0].name == "erk-managed-wt-01"
    assert loaded.slots[0].last_objective_issue is None


def test_update_slot_objective_sets_value() -> None:
    """Test that update_slot_objective sets the objective on the correct slot."""
    slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
    slot2 = SlotInfo(name="erk-managed-wt-02", last_objective_issue=None)
    state = PoolState.test(slots=(slot1, slot2))

    new_state = update_slot_objective(state, "erk-managed-wt-01", 123)

    assert new_state.slots[0].last_objective_issue == 123
    assert new_state.slots[1].last_objective_issue is None


def test_update_slot_objective_clears_value() -> None:
    """Test that update_slot_objective can clear an existing objective."""
    slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=123)
    state = PoolState.test(slots=(slot1,))

    new_state = update_slot_objective(state, "erk-managed-wt-01", None)

    assert new_state.slots[0].last_objective_issue is None


def test_update_slot_objective_replaces_value() -> None:
    """Test that update_slot_objective replaces an existing objective."""
    slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=100)
    state = PoolState.test(slots=(slot1,))

    new_state = update_slot_objective(state, "erk-managed-wt-01", 200)

    assert new_state.slots[0].last_objective_issue == 200


def test_update_slot_objective_returns_unchanged_for_unknown_slot() -> None:
    """Test that update_slot_objective returns state unchanged if slot not found."""
    slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
    state = PoolState.test(slots=(slot1,))

    new_state = update_slot_objective(state, "erk-managed-wt-99", 123)

    assert new_state is state  # Same object, unchanged


def test_update_slot_objective_preserves_other_fields() -> None:
    """Test that update_slot_objective preserves version, pool_size, assignments."""
    slot1 = SlotInfo(name="erk-managed-wt-01", last_objective_issue=None)
    assignment = SlotAssignment(
        slot_name="erk-managed-wt-01",
        branch_name="feature-a",
        assigned_at="2025-01-01T12:00:00+00:00",
        worktree_path=Path("/worktrees/wt-01"),
    )
    state = PoolState(
        version="2.0",
        pool_size=8,
        slots=(slot1,),
        assignments=(assignment,),
    )

    new_state = update_slot_objective(state, "erk-managed-wt-01", 42)

    assert new_state.version == "2.0"
    assert new_state.pool_size == 8
    assert new_state.assignments == (assignment,)
