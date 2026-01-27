"""Dry-run wrapper for git configuration operations."""

from pathlib import Path

from erk_shared.gateway.git.config_ops.abc import GitConfigOps


class DryRunGitConfigOps(GitConfigOps):
    """No-op wrapper that prevents execution of destructive operations.

    config_set is a no-op in dry-run mode.
    Query operations delegate to the wrapped implementation.
    """

    def __init__(self, wrapped: GitConfigOps) -> None:
        """Create a dry-run wrapper around a GitConfigOps implementation."""
        self._wrapped = wrapped

    # ============================================================================
    # Mutation Operations (no-ops in dry-run mode)
    # ============================================================================

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """No-op for config_set in dry-run mode."""

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_user_name(cwd)
