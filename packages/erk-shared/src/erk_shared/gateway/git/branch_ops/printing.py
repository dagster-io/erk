"""Printing Git branch operations wrapper for verbose output."""

from pathlib import Path

from erk_shared.gateway.git.abc import BranchDivergence, BranchSyncInfo
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.printing.base import PrintingBase


class PrintingGitBranchOps(PrintingBase, GitBranchOps):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for branch operations, then delegates to the
    wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production
        printing_ops = PrintingGitBranchOps(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGitBranchOps(real_ops)
        printing_ops = PrintingGitBranchOps(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    def create_branch(self, cwd: Path, branch_name: str, start_point: str, *, force: bool) -> None:
        """Create branch (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.create_branch(cwd, branch_name, start_point, force=force)

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete branch (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.delete_branch(cwd, branch_name, force=force)

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout branch with printed output."""
        self._emit(self._format_command(f"git checkout {branch}"))
        self._wrapped.checkout_branch(cwd, branch)

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout detached HEAD (delegates without printing for now)."""
        # No printing for detached HEAD in land-stack
        self._wrapped.checkout_detached(cwd, ref)

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create tracking branch (delegates without printing for now)."""
        self._wrapped.create_tracking_branch(repo_root, branch, remote_ref)

    # ============================================================================
    # Query Operations (pass-through delegation)
    # ============================================================================

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        return self._wrapped.get_current_branch(cwd)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository."""
        return self._wrapped.list_local_branches(repo_root)

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository."""
        return self._wrapped.list_remote_branches(repo_root)

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch."""
        return self._wrapped.get_branch_head(repo_root, branch)

    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name."""
        return self._wrapped.detect_trunk_branch(repo_root)

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate that a configured trunk branch exists."""
        return self._wrapped.validate_trunk_branch(repo_root, name)

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote."""
        return self._wrapped.branch_exists_on_remote(repo_root, remote, branch)

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get number of commits ahead and behind tracking branch."""
        return self._wrapped.get_ahead_behind(cwd, branch)

    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get sync status for all local branches."""
        return self._wrapped.get_all_branch_sync_info(repo_root)

    def is_branch_diverged_from_remote(
        self, cwd: Path, branch: str, remote: str
    ) -> BranchDivergence:
        """Check if a local branch has diverged from its remote tracking branch."""
        return self._wrapped.is_branch_diverged_from_remote(cwd, branch, remote)

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Extract GitHub issue number from branch name."""
        return self._wrapped.get_branch_issue(repo_root, branch)

    def get_behind_commit_authors(self, cwd: Path, branch: str) -> list[str]:
        """Get authors of commits on remote that are not in local branch."""
        return self._wrapped.get_behind_commit_authors(cwd, branch)

    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Get the author date of the most recent commit unique to a branch."""
        return self._wrapped.get_branch_last_commit_time(repo_root, branch, trunk)

    def get_branch_commits_with_authors(
        self, repo_root: Path, branch: str, trunk: str, *, limit: int
    ) -> list[dict[str, str]]:
        """Get commits on branch not on trunk, with author and timestamp."""
        return self._wrapped.get_branch_commits_with_authors(repo_root, branch, trunk, limit=limit)
