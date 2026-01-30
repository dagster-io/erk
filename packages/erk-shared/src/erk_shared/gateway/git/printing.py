"""Printing Git wrapper for verbose output.

This module provides a Git wrapper that prints styled output for operations
before delegating to the wrapped implementation.
"""

from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps
from erk_shared.gateway.git.analysis_ops.printing import PrintingGitAnalysisOps
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.git.branch_ops.printing import PrintingGitBranchOps
from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
from erk_shared.gateway.git.commit_ops.printing import PrintingGitCommitOps
from erk_shared.gateway.git.config_ops.abc import GitConfigOps
from erk_shared.gateway.git.config_ops.printing import PrintingGitConfigOps
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
from erk_shared.gateway.git.rebase_ops.printing import PrintingGitRebaseOps
from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.gateway.git.remote_ops.printing import PrintingGitRemoteOps
from erk_shared.gateway.git.repo_ops.abc import GitRepoOps
from erk_shared.gateway.git.repo_ops.printing import PrintingGitRepoOps
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.printing import PrintingGitStatusOps
from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.gateway.git.tag_ops.printing import PrintingGitTagOps
from erk_shared.gateway.git.worktree.abc import Worktree
from erk_shared.gateway.git.worktree.printing import PrintingWorktree
from erk_shared.printing.base import PrintingBase

# ============================================================================
# Printing Wrapper Implementation
# ============================================================================


class PrintingGit(PrintingBase, Git):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or Noop).

    Usage:
        # For production
        printing_ops = PrintingGit(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGit(real_ops)
        printing_ops = PrintingGit(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    @property
    def worktree(self) -> Worktree:
        """Access worktree operations subgateway (wrapped with PrintingWorktree)."""
        return PrintingWorktree(
            self._wrapped.worktree, script_mode=self._script_mode, dry_run=self._dry_run
        )

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway (wrapped with PrintingGitBranchOps)."""
        return PrintingGitBranchOps(
            self._wrapped.branch, script_mode=self._script_mode, dry_run=self._dry_run
        )

    @property
    def remote(self) -> GitRemoteOps:
        """Access remote operations subgateway (wrapped with PrintingGitRemoteOps)."""
        return PrintingGitRemoteOps(
            self._wrapped.remote, script_mode=self._script_mode, dry_run=self._dry_run
        )

    @property
    def commit(self) -> GitCommitOps:
        """Access commit operations subgateway (wrapped with PrintingGitCommitOps)."""
        return PrintingGitCommitOps(
            self._wrapped.commit, script_mode=self._script_mode, dry_run=self._dry_run
        )

    @property
    def status(self) -> GitStatusOps:
        """Access status operations subgateway (wrapped with PrintingGitStatusOps)."""
        return PrintingGitStatusOps(
            self._wrapped.status, script_mode=self._script_mode, dry_run=self._dry_run
        )

    @property
    def rebase(self) -> GitRebaseOps:
        """Access rebase operations subgateway (wrapped with PrintingGitRebaseOps)."""
        return PrintingGitRebaseOps(
            self._wrapped.rebase, script_mode=self._script_mode, dry_run=self._dry_run
        )

    @property
    def tag(self) -> GitTagOps:
        """Access tag operations subgateway (wrapped with PrintingGitTagOps)."""
        return PrintingGitTagOps(
            self._wrapped.tag, script_mode=self._script_mode, dry_run=self._dry_run
        )

    @property
    def repo(self) -> GitRepoOps:
        """Access repository location operations subgateway."""
        return PrintingGitRepoOps(
            self._wrapped.repo, script_mode=self._script_mode, dry_run=self._dry_run
        )

    @property
    def analysis(self) -> GitAnalysisOps:
        """Access branch analysis operations subgateway."""
        return PrintingGitAnalysisOps(
            self._wrapped.analysis, script_mode=self._script_mode, dry_run=self._dry_run
        )

    @property
    def config(self) -> GitConfigOps:
        """Access configuration operations subgateway."""
        return PrintingGitConfigOps(
            self._wrapped.config, script_mode=self._script_mode, dry_run=self._dry_run
        )
