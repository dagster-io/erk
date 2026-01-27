"""No-op Git tag operations wrapper for dry-run mode.

This module provides a wrapper that prevents execution of destructive
tag operations while delegating read-only operations to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.output.output import user_output


class DryRunGitTagOps(GitTagOps):
    """No-op wrapper that prevents execution of destructive tag operations.

    This wrapper intercepts destructive git operations (create_tag, push_tag) and
    prints what would happen. Read-only operations (tag_exists) are
    delegated to the wrapped implementation.

    Usage:
        real_ops = RealGitTagOps()
        noop_ops = DryRunGitTagOps(real_ops)

        # Query operations work normally
        exists = noop_ops.tag_exists(repo_root, "v1.0.0")

        # Mutation operations print dry-run message
        noop_ops.create_tag(repo_root, "v1.0.0", "Release")
    """

    def __init__(self, wrapped: GitTagOps) -> None:
        """Create a dry-run wrapper around a GitTagOps implementation.

        Args:
            wrapped: The GitTagOps implementation to wrap (usually RealGitTagOps)
        """
        self._wrapped = wrapped

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if tag exists (read-only, delegates to wrapped)."""
        return self._wrapped.tag_exists(repo_root, tag_name)

    # ============================================================================
    # Mutation Operations (print dry-run message)
    # ============================================================================

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Print dry-run message instead of creating tag."""
        user_output(f"[DRY RUN] Would run: git tag -a {tag_name} -m '{message}'")

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Print dry-run message instead of pushing tag."""
        user_output(f"[DRY RUN] Would run: git push {remote} {tag_name}")
