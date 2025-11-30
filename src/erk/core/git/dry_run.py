"""No-op Git wrapper for dry-run mode.

This module provides a Git wrapper that prevents execution of destructive
operations while delegating read-only operations to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.git.abc import BranchSyncInfo, Git, WorktreeInfo
from erk_shared.output.output import user_output

# ============================================================================
# No-op Wrapper
# ============================================================================


class DryRunGit(Git):
    """No-op wrapper that prevents execution of destructive operations.

    This wrapper intercepts destructive git operations and either returns without
    executing (for land-stack operations) or prints what would happen (for other
    operations). Read-only operations are delegated to the wrapped implementation.

    Usage:
        real_ops = RealGit()
        noop_ops = DryRunGit(real_ops)

        # No-op or prints message instead of deleting
        noop_ops.remove_worktree(repo_root, path, force=False)
    """

    def __init__(self, wrapped: Git) -> None:
        """Create a dry-run wrapper around a Git implementation.

        Args:
            wrapped: The Git implementation to wrap (usually RealGit or FakeGit)
        """
        self._wrapped = wrapped

    # Read-only operations: delegate to wrapped implementation

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees (read-only, delegates to wrapped)."""
        return self._wrapped.list_worktrees(repo_root)

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get current branch (read-only, delegates to wrapped)."""
        return self._wrapped.get_current_branch(cwd)

    def detect_default_branch(self, repo_root: Path, configured: str | None = None) -> str:
        """Detect default branch (read-only, delegates to wrapped)."""
        return self._wrapped.detect_default_branch(repo_root, configured)

    def get_trunk_branch(self, repo_root: Path) -> str:
        """Get trunk branch (read-only, delegates to wrapped)."""
        return self._wrapped.get_trunk_branch(repo_root)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List local branches (read-only, delegates to wrapped)."""
        return self._wrapped.list_local_branches(repo_root)

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List remote branches (read-only, delegates to wrapped)."""
        return self._wrapped.list_remote_branches(repo_root)

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """No-op for creating tracking branch in dry-run mode."""
        # Do nothing - prevents actual tracking branch creation
        pass

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get git common directory (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_common_dir(cwd)

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """No-op for checkout in dry-run mode."""
        # Do nothing - prevents actual checkout execution
        pass

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """No-op for detached checkout in dry-run mode."""
        # Do nothing - prevents actual detached HEAD checkout execution
        pass

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Print dry-run message instead of creating branch."""
        user_output(f"[DRY RUN] Would run: git branch {branch_name} {start_point}")

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Print dry-run message instead of deleting branch."""
        flag = "-D" if force else "-d"
        user_output(f"[DRY RUN] Would run: git branch {flag} {branch_name}")

    # Destructive operations: print dry-run message instead of executing

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check for staged changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_staged_changes(repo_root)

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check for uncommitted changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_uncommitted_changes(cwd)

    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Check if worktree is clean (read-only, delegates to wrapped)."""
        return self._wrapped.is_worktree_clean(worktree_path)

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Print dry-run message instead of adding worktree."""
        if branch and create_branch:
            base_ref = ref or "HEAD"
            user_output(f"[DRY RUN] Would run: git worktree add -b {branch} {path} {base_ref}")
        elif branch:
            user_output(f"[DRY RUN] Would run: git worktree add {path} {branch}")
        else:
            base_ref = ref or "HEAD"
            user_output(f"[DRY RUN] Would run: git worktree add {path} {base_ref}")

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Print dry-run message instead of moving worktree."""
        user_output(f"[DRY RUN] Would run: git worktree move {old_path} {new_path}")

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Print dry-run message instead of removing worktree."""
        force_flag = "--force " if force else ""
        user_output(f"[DRY RUN] Would run: git worktree remove {force_flag}{path}")

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Print dry-run message instead of deleting branch."""
        force_flag = "-f " if force else ""
        user_output(f"[DRY RUN] Would run: gt delete {force_flag}{branch}")

    def prune_worktrees(self, repo_root: Path) -> None:
        """Print dry-run message instead of pruning worktrees."""
        user_output("[DRY RUN] Would run: git worktree prune")

    def path_exists(self, path: Path) -> bool:
        """Check if path exists (read-only, delegates to wrapped)."""
        return self._wrapped.path_exists(path)

    def is_dir(self, path: Path) -> bool:
        """Check if path is directory (read-only, delegates to wrapped)."""
        return self._wrapped.is_dir(path)

    def safe_chdir(self, path: Path) -> bool:
        """Print dry-run message instead of changing directory."""
        would_succeed = self._wrapped.path_exists(path)
        if would_succeed:
            user_output(f"[DRY RUN] Would run: cd {path}")
        return False  # Never actually change directory in dry-run

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if branch is checked out (read-only, delegates to wrapped)."""
        return self._wrapped.is_branch_checked_out(repo_root, branch)

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for branch (read-only, delegates to wrapped)."""
        return self._wrapped.find_worktree_for_branch(repo_root, branch)

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get branch head commit SHA (read-only, delegates to wrapped)."""
        return self._wrapped.get_branch_head(repo_root, branch)

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get commit message (read-only, delegates to wrapped)."""
        return self._wrapped.get_commit_message(repo_root, commit_sha)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get file status (read-only, delegates to wrapped)."""
        return self._wrapped.get_file_status(cwd)

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get ahead/behind counts (read-only, delegates to wrapped)."""
        return self._wrapped.get_ahead_behind(cwd, branch)

    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get all branch sync info (read-only, delegates to wrapped)."""
        return self._wrapped.get_all_branch_sync_info(repo_root)

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commits (read-only, delegates to wrapped)."""
        return self._wrapped.get_recent_commits(cwd, limit=limit)

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """No-op for fetching branch in dry-run mode."""
        # Do nothing - prevents actual fetch execution
        pass

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """No-op for pulling branch in dry-run mode."""
        # Do nothing - prevents actual pull execution
        pass

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """No-op check - always returns True in dry-run mode."""
        # Return True to allow dry-run to continue
        return True

    def set_branch_issue(self, repo_root: Path, branch: str, issue_number: int) -> None:
        """No-op for setting branch issue in dry-run mode."""
        # Do nothing - prevents actual git config write
        pass

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Get branch issue (read-only, delegates to wrapped)."""
        return self._wrapped.get_branch_issue(repo_root, branch)

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        """No-op for fetching PR ref in dry-run mode."""
        # Do nothing - prevents actual fetch execution
        pass

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """No-op for staging files in dry-run mode."""
        # Do nothing - prevents actual file staging
        pass

    def commit(self, cwd: Path, message: str, *, allow_empty: bool = False) -> None:
        """No-op for committing in dry-run mode."""
        # Do nothing - prevents actual commit creation
        pass

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        """No-op for pushing in dry-run mode."""
        # Do nothing - prevents actual push execution
        pass
