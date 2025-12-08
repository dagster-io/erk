"""Printing Git wrapper for verbose output.

This module provides a Git wrapper that prints styled output for operations
before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.git.abc import BranchSyncInfo, Git, WorktreeInfo
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

    # Read-only operations: delegate without printing

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees (read-only, no printing)."""
        return self._wrapped.list_worktrees(repo_root)

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get current branch (read-only, no printing)."""
        return self._wrapped.get_current_branch(cwd)

    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect trunk branch (read-only, no printing)."""
        return self._wrapped.detect_trunk_branch(repo_root)

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate trunk branch exists (read-only, no printing)."""
        return self._wrapped.validate_trunk_branch(repo_root, name)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List local branches (read-only, no printing)."""
        return self._wrapped.list_local_branches(repo_root)

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List remote branches (read-only, no printing)."""
        return self._wrapped.list_remote_branches(repo_root)

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create tracking branch (read-only, no printing)."""
        return self._wrapped.create_tracking_branch(repo_root, branch, remote_ref)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get git common directory (read-only, no printing)."""
        return self._wrapped.get_git_common_dir(cwd)

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check for staged changes (read-only, no printing)."""
        return self._wrapped.has_staged_changes(repo_root)

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check for uncommitted changes (read-only, no printing)."""
        return self._wrapped.has_uncommitted_changes(cwd)

    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Check if worktree is clean (read-only, no printing)."""
        return self._wrapped.is_worktree_clean(worktree_path)

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if branch is checked out (read-only, no printing)."""
        return self._wrapped.is_branch_checked_out(repo_root, branch)

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get ahead/behind counts (read-only, no printing)."""
        return self._wrapped.get_ahead_behind(cwd, branch)

    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get all branch sync info (read-only, no printing)."""
        return self._wrapped.get_all_branch_sync_info(repo_root)

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commits (read-only, no printing)."""
        return self._wrapped.get_recent_commits(cwd, limit=limit)

    # Operations that need printing

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout branch with printed output."""
        self._emit(self._format_command(f"git checkout {branch}"))
        self._wrapped.checkout_branch(cwd, branch)

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout detached HEAD (delegates without printing for now)."""
        # No printing for detached HEAD in land-stack
        self._wrapped.checkout_detached(cwd, ref)

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create branch (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.create_branch(cwd, branch_name, start_point)

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete branch (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.delete_branch(cwd, branch_name, force=force)

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Add worktree (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.add_worktree(
            repo_root, path, branch=branch, ref=ref, create_branch=create_branch
        )

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move worktree (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.move_worktree(repo_root, old_path, new_path)

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Remove worktree (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.remove_worktree(repo_root, path, force=force)

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Delete branch with graphite (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.delete_branch_with_graphite(repo_root, branch, force=force)

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch branch with printed output."""
        self._emit(self._format_command(f"git fetch {remote} {branch}"))
        self._wrapped.fetch_branch(repo_root, remote, branch)

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull branch with printed output."""
        ff_flag = " --ff-only" if ff_only else ""
        self._emit(self._format_command(f"git pull{ff_flag} {remote} {branch}"))
        self._wrapped.pull_branch(repo_root, remote, branch, ff_only=ff_only)

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if branch exists on remote (delegates to wrapped implementation)."""
        # Read-only operation, no output needed
        return self._wrapped.branch_exists_on_remote(repo_root, remote, branch)

    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune worktrees (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.prune_worktrees(repo_root)

    def path_exists(self, path: Path) -> bool:
        """Check if path exists (read-only, no printing)."""
        return self._wrapped.path_exists(path)

    def is_dir(self, path: Path) -> bool:
        """Check if path is directory (read-only, no printing)."""
        return self._wrapped.is_dir(path)

    def safe_chdir(self, path: Path) -> bool:
        """Change directory (delegates to wrapped)."""
        return self._wrapped.safe_chdir(path)

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree for branch (read-only, no printing)."""
        return self._wrapped.find_worktree_for_branch(repo_root, branch)

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get branch head (read-only, no printing)."""
        return self._wrapped.get_branch_head(repo_root, branch)

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get commit message (read-only, no printing)."""
        return self._wrapped.get_commit_message(repo_root, commit_sha)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get file status (read-only, no printing)."""
        return self._wrapped.get_file_status(cwd)

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Get branch issue (read-only, no printing)."""
        return self._wrapped.get_branch_issue(repo_root, branch)

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        """Fetch PR ref with printed output."""
        self._emit(self._format_command(f"git fetch {remote} pull/{pr_number}/head:{local_branch}"))
        self._wrapped.fetch_pr_ref(repo_root, remote, pr_number, local_branch)

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Stage files with printed output."""
        self._emit(self._format_command(f"git add {' '.join(paths)}"))
        self._wrapped.stage_files(cwd, paths)

    def commit(self, cwd: Path, message: str) -> None:
        """Commit with printed output."""
        # Truncate message for display
        display_msg = message[:50] + "..." if len(message) > 50 else message
        self._emit(self._format_command(f'git commit --allow-empty -m "{display_msg}"'))
        self._wrapped.commit(cwd, message)

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        """Push to remote with printed output."""
        upstream_flag = "-u " if set_upstream else ""
        self._emit(self._format_command(f"git push {upstream_flag}{remote} {branch}"))
        self._wrapped.push_to_remote(cwd, remote, branch, set_upstream=set_upstream)

    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Get branch last commit time (read-only, no printing)."""
        return self._wrapped.get_branch_last_commit_time(repo_root, branch, trunk)

    def add_all(self, cwd: Path) -> None:
        """Stage all changes with printed output."""
        self._emit(self._format_command("git add -A"))
        self._wrapped.add_all(cwd)

    def amend_commit(self, cwd: Path, message: str) -> None:
        """Amend commit with printed output."""
        display_msg = message[:50] + "..." if len(message) > 50 else message
        self._emit(self._format_command(f'git commit --amend -m "{display_msg}"'))
        self._wrapped.amend_commit(cwd, message)

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

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        """Get remote URL (read-only, no printing)."""
        return self._wrapped.get_remote_url(repo_root, remote)

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get conflicted files (read-only, no printing)."""
        return self._wrapped.get_conflicted_files(cwd)

    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check if rebase in progress (read-only, no printing)."""
        return self._wrapped.is_rebase_in_progress(cwd)

    def rebase_continue(self, cwd: Path) -> None:
        """Continue rebase (delegates without printing for now)."""
        self._wrapped.rebase_continue(cwd)

    def get_commit_messages_since(self, cwd: Path, base_branch: str) -> list[str]:
        """Get commit messages since base branch (read-only, no printing)."""
        return self._wrapped.get_commit_messages_since(cwd, base_branch)
