"""Printing Git wrapper for verbose output.

This module provides a Git wrapper that prints styled output for operations
before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.abc import BranchDivergence, BranchSyncInfo, Git, RebaseResult
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

    # Read-only operations: delegate without printing

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get current branch (read-only, no printing)."""
        return self._wrapped.branch.get_current_branch(cwd)

    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect trunk branch (read-only, no printing)."""
        return self._wrapped.branch.detect_trunk_branch(repo_root)

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate trunk branch exists (read-only, no printing)."""
        return self._wrapped.branch.validate_trunk_branch(repo_root, name)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List local branches (read-only, no printing)."""
        return self._wrapped.branch.list_local_branches(repo_root)

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List remote branches (read-only, no printing)."""
        return self._wrapped.branch.list_remote_branches(repo_root)

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get ahead/behind counts (read-only, no printing)."""
        return self._wrapped.branch.get_ahead_behind(cwd, branch)

    def get_behind_commit_authors(self, cwd: Path, branch: str) -> list[str]:
        """Get behind commit authors (read-only, no printing)."""
        return self._wrapped.branch.get_behind_commit_authors(cwd, branch)

    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get all branch sync info (read-only, no printing)."""
        return self._wrapped.branch.get_all_branch_sync_info(repo_root)

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if branch exists on remote (delegates to wrapped implementation)."""
        # Read-only operation, no output needed
        return self._wrapped.branch.branch_exists_on_remote(repo_root, remote, branch)

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get branch head (read-only, no printing)."""
        return self._wrapped.branch.get_branch_head(repo_root, branch)

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Get branch issue (read-only, no printing)."""
        return self._wrapped.branch.get_branch_issue(repo_root, branch)

    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Get branch last commit time (read-only, no printing)."""
        return self._wrapped.branch.get_branch_last_commit_time(repo_root, branch, trunk)

    def get_branch_commits_with_authors(
        self, repo_root: Path, branch: str, trunk: str, *, limit: int = 50
    ) -> list[dict[str, str]]:
        """Get branch commits with authors (read-only, no printing)."""
        return self._wrapped.branch.get_branch_commits_with_authors(
            repo_root, branch, trunk, limit=limit
        )

    def is_branch_diverged_from_remote(
        self, cwd: Path, branch: str, remote: str
    ) -> BranchDivergence:
        """Check branch divergence (read-only, no printing)."""
        return self._wrapped.branch.is_branch_diverged_from_remote(cwd, branch, remote)

    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """Rebase onto target ref with printed output."""
        self._emit(self._format_command(f"git rebase {target_ref}"))
        return self._wrapped.rebase_onto(cwd, target_ref)

    def rebase_abort(self, cwd: Path) -> None:
        """Abort rebase with printed output."""
        self._emit(self._format_command("git rebase --abort"))
        self._wrapped.rebase_abort(cwd)
