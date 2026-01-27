"""Dry-run wrapper for git analysis operations."""

from pathlib import Path

from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps


class DryRunGitAnalysisOps(GitAnalysisOps):
    """Dry-run wrapper that delegates read-only operations.

    All operations in AnalysisOps are read-only, so this simply delegates.
    """

    def __init__(self, wrapped: GitAnalysisOps) -> None:
        """Create a dry-run wrapper around a GitAnalysisOps implementation."""
        self._wrapped = wrapped

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.count_commits_ahead(cwd, base_branch)

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_merge_base(repo_root, ref1, ref2)

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_diff_to_branch(cwd, branch)
