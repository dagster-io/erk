"""No-op Git rebase operations wrapper for dry-run mode.

This module provides a wrapper that prevents execution of destructive
rebase operations while delegating read-only operations to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.abc import RebaseResult
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps


class DryRunGitRebaseOps(GitRebaseOps):
    """No-op wrapper that prevents execution of destructive rebase operations.

    This wrapper intercepts destructive git operations (rebase_onto, rebase_continue,
    rebase_abort) and returns without executing. Read-only operations (is_rebase_in_progress)
    are delegated to the wrapped implementation.
    """

    def __init__(self, wrapped: GitRebaseOps) -> None:
        """Create a dry-run wrapper around a GitRebaseOps implementation.

        Args:
            wrapped: The GitRebaseOps implementation to wrap
        """
        self._wrapped = wrapped

    # ============================================================================
    # Mutation Operations (no-ops in dry-run mode)
    # ============================================================================

    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """No-op for rebase in dry-run mode. Returns success."""
        return RebaseResult(success=True, conflict_files=())

    def rebase_continue(self, cwd: Path) -> None:
        """No-op for continuing rebase in dry-run mode."""
        pass

    def rebase_abort(self, cwd: Path) -> None:
        """No-op for rebase abort in dry-run mode."""
        pass

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check if rebase in progress (read-only, delegates to wrapped)."""
        return self._wrapped.is_rebase_in_progress(cwd)
