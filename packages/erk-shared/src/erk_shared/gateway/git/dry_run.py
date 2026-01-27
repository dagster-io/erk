"""No-op Git wrapper for dry-run mode.

This module provides a Git wrapper that prevents execution of destructive
operations while delegating read-only operations to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.git.branch_ops.dry_run import DryRunGitBranchOps
from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
from erk_shared.gateway.git.commit_ops.dry_run import DryRunGitCommitOps
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
from erk_shared.gateway.git.rebase_ops.dry_run import DryRunGitRebaseOps
from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.gateway.git.remote_ops.dry_run import DryRunGitRemoteOps
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.dry_run import DryRunGitStatusOps
from erk_shared.gateway.git.worktree.abc import Worktree
from erk_shared.gateway.git.worktree.dry_run import DryRunWorktree
from erk_shared.output.output import user_output

# ============================================================================
# No-op Wrapper
# ============================================================================


class DryRunGit(Git):
    """No-op wrapper that prevents execution of destructive operations.

    This wrapper intercepts destructive git operations and either returns without
    executing (for land-stack operations) or prints what would happen (for other
    operations). Read-only operations are delegated to the wrapped implementation.

    Worktree operations are handled by the DryRunWorktree subgateway, accessible
    via the worktree property.

    Usage:
        real_ops = RealGit()
        noop_ops = DryRunGit(real_ops)

        # Worktree operations go through subgateway
        noop_ops.worktree.remove_worktree(repo_root, path, force=False)
    """

    def __init__(self, wrapped: Git) -> None:
        """Create a dry-run wrapper around a Git implementation.

        Args:
            wrapped: The Git implementation to wrap (usually RealGit or FakeGit)
        """
        self._wrapped = wrapped

    @property
    def worktree(self) -> Worktree:
        """Access worktree operations subgateway (wrapped with DryRunWorktree)."""
        return DryRunWorktree(self._wrapped.worktree)

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway (wrapped with DryRunGitBranchOps)."""
        return DryRunGitBranchOps(self._wrapped.branch)

    @property
    def remote(self) -> GitRemoteOps:
        """Access remote operations subgateway (wrapped with DryRunGitRemoteOps)."""
        return DryRunGitRemoteOps(self._wrapped.remote)

    @property
    def commit(self) -> GitCommitOps:
        """Access commit operations subgateway (wrapped with DryRunGitCommitOps)."""
        return DryRunGitCommitOps(self._wrapped.commit)

    @property
    def status(self) -> GitStatusOps:
        """Access status operations subgateway (wrapped with DryRunGitStatusOps)."""
        return DryRunGitStatusOps(self._wrapped.status)

    @property
    def rebase(self) -> GitRebaseOps:
        """Access rebase operations subgateway (wrapped with DryRunGitRebaseOps)."""
        return DryRunGitRebaseOps(self._wrapped.rebase)

    # Read-only operations: delegate to wrapped implementation

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get git common directory (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_common_dir(cwd)

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits ahead (read-only, delegates to wrapped)."""
        return self._wrapped.count_commits_ahead(cwd, base_branch)

    def get_repository_root(self, cwd: Path) -> Path:
        """Get repository root (read-only, delegates to wrapped)."""
        return self._wrapped.get_repository_root(cwd)

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff to branch (read-only, delegates to wrapped)."""
        return self._wrapped.get_diff_to_branch(cwd, branch)

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str = "local") -> None:
        """No-op for setting git config in dry-run mode."""
        pass

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get git user.name (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_user_name(cwd)

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if tag exists (read-only, delegates to wrapped)."""
        return self._wrapped.tag_exists(repo_root, tag_name)

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Print dry-run message instead of creating tag."""
        user_output(f"[DRY RUN] Would run: git tag -a {tag_name} -m '{message}'")

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Print dry-run message instead of pushing tag."""
        user_output(f"[DRY RUN] Would run: git push {remote} {tag_name}")

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get merge base (read-only, delegates to wrapped)."""
        return self._wrapped.get_merge_base(repo_root, ref1, ref2)
