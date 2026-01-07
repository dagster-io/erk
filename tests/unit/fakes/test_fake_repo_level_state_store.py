"""Unit tests for FakeRepoLevelStateStore.

Layer 1 tests: Verify the fake implementation works correctly.
"""

from pathlib import Path

from erk.core.worktree_pool import PoolState, SlotAssignment
from erk_shared.gateway.repo_state.fake import FakeRepoLevelStateStore


def test_load_pool_state_returns_none_by_default() -> None:
    """Test that load_pool_state returns None when not configured."""
    fake = FakeRepoLevelStateStore()

    result = fake.load_pool_state(Path("/some/path/pool.json"))

    assert result is None


def test_load_pool_state_returns_configured_initial_state() -> None:
    """Test that load_pool_state returns the configured initial state."""
    initial_state = PoolState.test()
    fake = FakeRepoLevelStateStore(initial_pool_state=initial_state)

    result = fake.load_pool_state(Path("/some/path/pool.json"))

    assert result is initial_state


def test_save_pool_state_updates_internal_state() -> None:
    """Test that save_pool_state updates the stored state."""
    fake = FakeRepoLevelStateStore()
    new_state = PoolState.test()

    fake.save_pool_state(Path("/some/path/pool.json"), new_state)

    assert fake.load_pool_state(Path("/any/path")) == new_state


def test_save_pool_state_tracks_all_saves() -> None:
    """Test that pool_saves tracks all save calls with path and state."""
    fake = FakeRepoLevelStateStore()
    path1 = Path("/repo1/pool.json")
    path2 = Path("/repo2/pool.json")
    state1 = PoolState.test()
    state2 = PoolState.test(
        assignments=(
            SlotAssignment(
                slot_name="slot-01",
                branch_name="feature",
                assigned_at="2024-01-01T00:00:00Z",
                worktree_path=Path("/worktree"),
            ),
        )
    )

    fake.save_pool_state(path1, state1)
    fake.save_pool_state(path2, state2)

    assert fake.pool_saves == ((path1, state1), (path2, state2))


def test_pool_saves_returns_tuple_to_prevent_mutation() -> None:
    """Test that pool_saves returns a tuple (immutable)."""
    fake = FakeRepoLevelStateStore()
    fake.save_pool_state(Path("/path/pool.json"), PoolState.test())

    saves = fake.pool_saves

    assert isinstance(saves, tuple)


def test_current_pool_state_returns_none_when_empty() -> None:
    """Test that current_pool_state returns None when not configured."""
    fake = FakeRepoLevelStateStore()

    assert fake.current_pool_state is None


def test_current_pool_state_returns_initial_state() -> None:
    """Test that current_pool_state returns the initial state."""
    initial_state = PoolState.test()
    fake = FakeRepoLevelStateStore(initial_pool_state=initial_state)

    assert fake.current_pool_state is initial_state


def test_current_pool_state_reflects_latest_save() -> None:
    """Test that current_pool_state reflects the most recent save."""
    initial_state = PoolState.test()
    fake = FakeRepoLevelStateStore(initial_pool_state=initial_state)

    new_state = PoolState.test(
        assignments=(
            SlotAssignment(
                slot_name="slot-02",
                branch_name="new-feature",
                assigned_at="2024-01-02T00:00:00Z",
                worktree_path=Path("/worktree2"),
            ),
        )
    )
    fake.save_pool_state(Path("/path/pool.json"), new_state)

    assert fake.current_pool_state is new_state


def test_load_ignores_path_argument() -> None:
    """Test that load_pool_state ignores the path and returns stored state."""
    initial_state = PoolState.test()
    fake = FakeRepoLevelStateStore(initial_pool_state=initial_state)

    # Load from different paths should all return the same state
    result1 = fake.load_pool_state(Path("/path1/pool.json"))
    result2 = fake.load_pool_state(Path("/path2/pool.json"))
    result3 = fake.load_pool_state(Path("/completely/different/location.json"))

    assert result1 is initial_state
    assert result2 is initial_state
    assert result3 is initial_state
