"""Printing Git wrapper for verbose output.

This module provides a Git wrapper that prints styled output for operations
before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.abc import BranchDivergence, BranchSyncInfo, Git, RebaseResult
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.git.branch_ops.printing import PrintingGitBranchOps
from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
from erk_shared.gateway.git.commit_ops.printing import PrintingGitCommitOps
from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.gateway.git.remote_ops.printing import PrintingGitRemoteOps
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

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get git common directory (read-only, no printing)."""
        return self._wrapped.get_git_common_dir(cwd)

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check for staged changes (read-only, no printing)."""
        return self._wrapped.has_staged_changes(repo_root)

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check for uncommitted changes (read-only, no printing)."""
        return self._wrapped.has_uncommitted_changes(cwd)

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

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get file status (read-only, no printing)."""
        return self._wrapped.get_file_status(cwd)

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Get branch issue (read-only, no printing)."""
        return self._wrapped.branch.get_branch_issue(repo_root, branch)

    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Get branch last commit time (read-only, no printing)."""
        return self._wrapped.branch.get_branch_last_commit_time(repo_root, branch, trunk)

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits ahead (read-only, no printing)."""
        return self._wrapped.count_commits_ahead(cwd, base_branch)

    def get_repository_root(self, cwd: Path) -> Path:
        """Get repository root (read-only, no printing)."""
        return self._wrapped.get_repository_root(cwd)

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff to branch (read-only, no printing)."""
        return self._wrapped.get_diff_to_branch(cwd, branch)

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check merge conflicts (read-only, no printing)."""
        return self._wrapped.check_merge_conflicts(cwd, base_branch, head_branch)

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get conflicted files (read-only, no printing)."""
        return self._wrapped.get_conflicted_files(cwd)

    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check if rebase in progress (read-only, no printing)."""
        return self._wrapped.is_rebase_in_progress(cwd)

    def rebase_continue(self, cwd: Path) -> None:
        """Continue rebase (delegates without printing for now)."""
        self._wrapped.rebase_continue(cwd)

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str = "local") -> None:
        """Set git config with printed output."""
        self._emit(self._format_command(f"git config --{scope} {key} {value}"))
        self._wrapped.config_set(cwd, key, value, scope=scope)

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get git user.name (read-only, no printing)."""
        return self._wrapped.get_git_user_name(cwd)

    def get_branch_commits_with_authors(
        self, repo_root: Path, branch: str, trunk: str, *, limit: int = 50
    ) -> list[dict[str, str]]:
        """Get branch commits with authors (read-only, no printing)."""
        return self._wrapped.branch.get_branch_commits_with_authors(
            repo_root, branch, trunk, limit=limit
        )

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if tag exists (read-only, no printing)."""
        return self._wrapped.tag_exists(repo_root, tag_name)

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create tag with printed output."""
        self._emit(self._format_command(f"git tag -a {tag_name} -m '{message}'"))
        self._wrapped.create_tag(repo_root, tag_name, message)

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push tag with printed output."""
        self._emit(self._format_command(f"git push {remote} {tag_name}"))
        self._wrapped.push_tag(repo_root, remote, tag_name)

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

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get merge base (read-only, no printing)."""
        return self._wrapped.get_merge_base(repo_root, ref1, ref2)
