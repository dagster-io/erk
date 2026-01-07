"""Dry-run implementation of RepoLevelStateStore."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.gateway.repo_state.abc import RepoLevelStateStore
from erk_shared.output.output import user_output

if TYPE_CHECKING:
    from erk.core.worktree_pool import PoolState


class DryRunRepoLevelStateStore(RepoLevelStateStore):
    """Dry-run wrapper that prints instead of writing.

    This wrapper intercepts write operations and prints what would happen
    instead of executing. Read operations are delegated to the wrapped
    implementation.

    Usage:
        real_store = RealRepoLevelStateStore()
        dry_run_store = DryRunRepoLevelStateStore(real_store)

        # Reads work normally
        state = dry_run_store.load_pool_state(path)

        # Writes print instead of persisting
        dry_run_store.save_pool_state(path, new_state)
        # Output: [DRY RUN] Would save pool state to /path/to/pool.json
    """

    def __init__(self, wrapped: RepoLevelStateStore) -> None:
        """Create a dry-run wrapper around a RepoLevelStateStore implementation.

        Args:
            wrapped: The RepoLevelStateStore implementation to wrap
        """
        self._wrapped = wrapped

    def load_pool_state(self, pool_json_path: Path) -> PoolState | None:
        """Load pool state - delegates to wrapped (read-only operation).

        Args:
            pool_json_path: Path to the pool.json file

        Returns:
            PoolState if file exists and is valid, None otherwise
        """
        return self._wrapped.load_pool_state(pool_json_path)

    def save_pool_state(self, pool_json_path: Path, state: PoolState) -> None:
        """Print what would be saved instead of actually saving.

        Args:
            pool_json_path: Path to the pool.json file
            state: Pool state that would be persisted
        """
        user_output(f"[DRY RUN] Would save pool state to {pool_json_path}")
