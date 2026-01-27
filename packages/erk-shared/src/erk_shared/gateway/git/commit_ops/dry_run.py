"""No-op Git commit operations wrapper for dry-run mode.

This module provides a wrapper that prevents execution of destructive
commit operations while delegating read-only operations to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.commit_ops.abc import GitCommitOps


class DryRunGitCommitOps(GitCommitOps):
    """No-op wrapper that prevents execution of destructive commit operations.

    This wrapper intercepts destructive git operations (stage, commit, amend) and
    returns without executing. Read-only operations (get_commit_message, etc.) are
    delegated to the wrapped implementation.

    Usage:
        real_ops = RealGitCommitOps(time)
        noop_ops = DryRunGitCommitOps(real_ops)

        # Query operations work normally
        message = noop_ops.get_commit_message(repo_root, "abc123")

        # Mutation operations are no-ops
        noop_ops.commit(cwd, "message")
    """

    def __init__(self, wrapped: GitCommitOps) -> None:
        """Create a dry-run wrapper around a GitCommitOps implementation.

        Args:
            wrapped: The GitCommitOps implementation to wrap (usually RealGitCommitOps)
        """
        self._wrapped = wrapped

    # ============================================================================
    # Mutation Operations (no-ops in dry-run mode)
    # ============================================================================

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """No-op for staging files in dry-run mode."""
        # Do nothing - prevents actual file staging
        pass

    def commit(self, cwd: Path, message: str) -> None:
        """No-op for committing in dry-run mode."""
        # Do nothing - prevents actual commit creation
        pass

    def add_all(self, cwd: Path) -> None:
        """No-op for staging all changes in dry-run mode."""
        # Do nothing - prevents actual staging
        pass

    def amend_commit(self, cwd: Path, message: str) -> None:
        """No-op for amending commit in dry-run mode."""
        # Do nothing - prevents actual commit amendment
        pass

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get commit message (read-only, delegates to wrapped)."""
        return self._wrapped.get_commit_message(repo_root, commit_sha)

    def get_commit_messages_since(self, cwd: Path, base_branch: str) -> list[str]:
        """Get commit messages since base branch (read-only, delegates to wrapped)."""
        return self._wrapped.get_commit_messages_since(cwd, base_branch)

    def get_head_commit_message_full(self, cwd: Path) -> str:
        """Get full commit message (read-only, delegates to wrapped)."""
        return self._wrapped.get_head_commit_message_full(cwd)

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commits (read-only, delegates to wrapped)."""
        return self._wrapped.get_recent_commits(cwd, limit=limit)
