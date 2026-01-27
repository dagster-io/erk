"""Printing wrapper for git repository operations."""

from pathlib import Path

from erk_shared.gateway.git.repo_ops.abc import GitRepoOps
from erk_shared.printing.base import PrintingBase


class PrintingGitRepoOps(PrintingBase, GitRepoOps):
    """Wrapper that delegates without printing (all operations are read-only)."""

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_repository_root(cwd)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_git_common_dir(cwd)
