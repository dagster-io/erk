"""No-op Git wrapper for dry-run mode.

This module provides a Git wrapper that prevents execution of destructive
operations while delegating read-only operations to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.abc import Git, RebaseResult
from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps
from erk_shared.gateway.git.analysis_ops.dry_run import DryRunGitAnalysisOps
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.git.branch_ops.dry_run import DryRunGitBranchOps
from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
from erk_shared.gateway.git.commit_ops.dry_run import DryRunGitCommitOps
from erk_shared.gateway.git.config_ops.abc import GitConfigOps
from erk_shared.gateway.git.config_ops.dry_run import DryRunGitConfigOps
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
from erk_shared.gateway.git.rebase_ops.dry_run import DryRunGitRebaseOps
from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.gateway.git.remote_ops.dry_run import DryRunGitRemoteOps
from erk_shared.gateway.git.repo_ops.abc import GitRepoOps
from erk_shared.gateway.git.repo_ops.dry_run import DryRunGitRepoOps
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.dry_run import DryRunGitStatusOps
from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.gateway.git.tag_ops.dry_run import DryRunGitTagOps
from erk_shared.gateway.git.worktree.abc import Worktree
from erk_shared.gateway.git.worktree.dry_run import DryRunWorktree

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

    @property
    def tag(self) -> GitTagOps:
        """Access tag operations subgateway (wrapped with DryRunGitTagOps)."""
        return DryRunGitTagOps(self._wrapped.tag)

    @property
    def repo(self) -> GitRepoOps:
        """Access repository location operations subgateway."""
        return DryRunGitRepoOps(self._wrapped.repo)

    @property
    def analysis(self) -> GitAnalysisOps:
        """Access branch analysis operations subgateway."""
        return DryRunGitAnalysisOps(self._wrapped.analysis)

    @property
    def config(self) -> GitConfigOps:
        """Access configuration operations subgateway."""
        return DryRunGitConfigOps(self._wrapped.config)

    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """No-op for rebase in dry-run mode. Returns success."""
        return RebaseResult(success=True, conflict_files=())

    def rebase_abort(self, cwd: Path) -> None:
        """No-op for rebase abort in dry-run mode."""
        pass
