"""Printing wrapper for repo-level state store operations."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from erk_shared.gateway.repo_state.abc import RepoLevelStateStore
from erk_shared.printing.base import PrintingBase

if TYPE_CHECKING:
    from erk.core.worktree_pool import PoolState


class PrintingRepoLevelStateStore(PrintingBase, RepoLevelStateStore):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for mutation operations, then delegates to
    the wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production
        printing_store = PrintingRepoLevelStateStore(real_store, script_mode=False, dry_run=False)

        # For dry-run
        dry_run_inner = DryRunRepoLevelStateStore(real_store)
        printing_store = PrintingRepoLevelStateStore(dry_run_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # Read-only operations: delegate without printing

    def load_pool_state(self, pool_json_path: Path) -> PoolState | None:
        """Load pool state (read-only, no printing)."""
        return self._wrapped.load_pool_state(pool_json_path)

    # Mutation operations: print before delegating

    def save_pool_state(self, pool_json_path: Path, state: PoolState) -> None:
        """Save pool state with printed output."""
        self._emit(self._format_command(f"write {pool_json_path}"))
        self._wrapped.save_pool_state(pool_json_path, state)
