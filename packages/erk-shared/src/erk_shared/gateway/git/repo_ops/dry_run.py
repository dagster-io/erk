"""Dry-run wrapper for git repository operations."""

from pathlib import Path

from erk_shared.gateway.git.repo_ops.abc import GitRepoOps


class DryRunGitRepoOps(GitRepoOps):
    """Dry-run wrapper that delegates read-only operations.

    All operations in RepoOps are read-only, so this simply delegates.
    """

    def __init__(self, wrapped: GitRepoOps) -> None:
        """Create a dry-run wrapper around a GitRepoOps implementation."""
        self._wrapped = wrapped

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_repository_root(cwd)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_common_dir(cwd)
