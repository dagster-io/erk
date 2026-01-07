"""Abstract base class for repo-level state file operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk.core.worktree_pool import PoolState


class RepoLevelStateStore(ABC):
    """Abstract interface for repo-level state file operations.

    This gateway provides access to repo-level state files stored in
    ~/.erk/repos/<repo>/, such as pool.json. The gateway pattern ensures
    tests use FakeRepoLevelStateStore which never accesses the real filesystem.

    Naming convention:
    - User-level: ~/.claude/ -> UserLevelClaudeSettingsStore
    - Repo-level: ~/.erk/repos/<repo>/ -> RepoLevelStateStore

    Three implementations:
    - RealRepoLevelStateStore: Production - reads/writes real filesystem
    - FakeRepoLevelStateStore: Testing - in-memory storage, never touches disk
    - DryRunRepoLevelStateStore: Preview - reads real, no-ops writes
    """

    @abstractmethod
    def load_pool_state(self, pool_json_path: Path) -> PoolState | None:
        """Load pool state from JSON file.

        Args:
            pool_json_path: Path to the pool.json file

        Returns:
            PoolState if file exists and is valid, None otherwise
        """
        ...

    @abstractmethod
    def save_pool_state(self, pool_json_path: Path, state: PoolState) -> None:
        """Save pool state to JSON file.

        Creates parent directories if they don't exist.

        Args:
            pool_json_path: Path to the pool.json file
            state: Pool state to persist
        """
        ...
