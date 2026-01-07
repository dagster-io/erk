"""Fake implementation of RepoLevelStateStore for testing."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.gateway.repo_state.abc import RepoLevelStateStore

if TYPE_CHECKING:
    from erk.core.worktree_pool import PoolState


class FakeRepoLevelStateStore(RepoLevelStateStore):
    """Test implementation - in-memory storage, no filesystem access.

    This fake provides:
    - In-memory storage that never touches the real filesystem
    - Constructor injection for initial state
    - Mutation tracking via read-only properties

    Usage:
        # Basic usage - empty store
        store = FakeRepoLevelStateStore()

        # Pre-populated with initial pool state
        store = FakeRepoLevelStateStore(
            initial_pool_state=PoolState.test()
        )

        # Verify saves in tests
        store.save_pool_state(path, new_state)
        assert len(store.pool_saves) == 1
        assert store.pool_saves[0] == (path, new_state)
    """

    def __init__(
        self,
        *,
        initial_pool_state: PoolState | None = None,
    ) -> None:
        """Initialize fake store with optional pre-populated state.

        Args:
            initial_pool_state: Optional PoolState to pre-populate the store
                for testing scenarios. If None, load_pool_state returns None.
        """
        self._pool_state = initial_pool_state
        self._pool_saves: list[tuple[Path, PoolState]] = []

    def load_pool_state(self, pool_json_path: Path) -> PoolState | None:
        """Load pool state from in-memory storage.

        Args:
            pool_json_path: Path to the pool.json file (ignored in fake)

        Returns:
            Stored PoolState, or None if not set
        """
        return self._pool_state

    def save_pool_state(self, pool_json_path: Path, state: PoolState) -> None:
        """Save pool state to in-memory storage.

        Args:
            pool_json_path: Path to the pool.json file
            state: Pool state to store
        """
        self._pool_state = state
        self._pool_saves.append((pool_json_path, state))

    @property
    def pool_saves(self) -> tuple[tuple[Path, PoolState], ...]:
        """Read-only access to all saves for test assertions.

        Returns:
            Tuple of (path, state) for each save that occurred
        """
        return tuple(self._pool_saves)

    @property
    def current_pool_state(self) -> PoolState | None:
        """Read-only access to current pool state.

        Returns:
            Current PoolState or None
        """
        return self._pool_state
