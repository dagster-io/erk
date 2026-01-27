"""No-op Git status operations wrapper for dry-run mode.

Since all status operations are read-only queries, this wrapper
simply delegates all calls to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.status_ops.abc import GitStatusOps


class DryRunGitStatusOps(GitStatusOps):
    """Pass-through wrapper for status operations in dry-run mode.

    All status operations are read-only queries, so they are simply
    delegated to the wrapped implementation without modification.

    Usage:
        real_ops = RealGitStatusOps()
        dry_run_ops = DryRunGitStatusOps(real_ops)

        # All operations delegate to wrapped
        has_staged = dry_run_ops.has_staged_changes(repo_root)
    """

    def __init__(self, wrapped: GitStatusOps) -> None:
        """Create a dry-run wrapper around a GitStatusOps implementation.

        Args:
            wrapped: The GitStatusOps implementation to wrap (usually RealGitStatusOps)
        """
        self._wrapped = wrapped

    # ============================================================================
    # All operations are read-only - delegate directly
    # ============================================================================

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check for staged changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_staged_changes(repo_root)

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check for uncommitted changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_uncommitted_changes(cwd)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get file status (read-only, delegates to wrapped)."""
        return self._wrapped.get_file_status(cwd)

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check merge conflicts (read-only, delegates to wrapped)."""
        return self._wrapped.check_merge_conflicts(cwd, base_branch, head_branch)

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get conflicted files (read-only, delegates to wrapped)."""
        return self._wrapped.get_conflicted_files(cwd)
