"""Printing wrapper for git analysis operations."""

from pathlib import Path

from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps
from erk_shared.printing.base import PrintingBase


class PrintingGitAnalysisOps(PrintingBase, GitAnalysisOps):
    """Wrapper that delegates without printing (all operations are read-only)."""

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Query operation (read-only, no printing)."""
        return self._wrapped.count_commits_ahead(cwd, base_branch)

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_merge_base(repo_root, ref1, ref2)

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_diff_to_branch(cwd, branch)
