"""No-op Git remote operations wrapper for dry-run mode.

This module provides a wrapper that prevents execution of destructive
remote operations while delegating read-only operations to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps


class DryRunGitRemoteOps(GitRemoteOps):
    """No-op wrapper that prevents execution of destructive remote operations.

    This wrapper intercepts destructive git operations (fetch, pull, push) and
    returns without executing. Read-only operations (get_remote_url) are delegated
    to the wrapped implementation.

    Usage:
        real_ops = RealGitRemoteOps(time)
        noop_ops = DryRunGitRemoteOps(real_ops)

        # Query operations work normally
        url = noop_ops.get_remote_url(repo_root, "origin")

        # Mutation operations are no-ops
        noop_ops.push_to_remote(cwd, "origin", "main", set_upstream=True, force=False)
    """

    def __init__(self, wrapped: GitRemoteOps) -> None:
        """Create a dry-run wrapper around a GitRemoteOps implementation.

        Args:
            wrapped: The GitRemoteOps implementation to wrap (usually RealGitRemoteOps)
        """
        self._wrapped = wrapped

    # ============================================================================
    # Mutation Operations (no-ops in dry-run mode)
    # ============================================================================

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """No-op for fetching branch in dry-run mode."""
        # Do nothing - prevents actual fetch execution
        pass

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """No-op for pulling branch in dry-run mode."""
        # Do nothing - prevents actual pull execution
        pass

    def fetch_pr_ref(
        self, *, repo_root: Path, remote: str, pr_number: int, local_branch: str
    ) -> None:
        """No-op for fetching PR ref in dry-run mode."""
        # Do nothing - prevents actual fetch execution
        pass

    def push_to_remote(
        self,
        cwd: Path,
        remote: str,
        branch: str,
        *,
        set_upstream: bool,
        force: bool,
    ) -> None:
        """No-op for pushing in dry-run mode."""
        # Do nothing - prevents actual push execution
        pass

    def pull_rebase(self, cwd: Path, remote: str, branch: str) -> None:
        """No-op for pull --rebase in dry-run mode."""
        pass

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def get_remote_url(self, repo_root: Path, remote: str) -> str:
        """Get remote URL (read-only, delegates to wrapped)."""
        return self._wrapped.get_remote_url(repo_root, remote)
