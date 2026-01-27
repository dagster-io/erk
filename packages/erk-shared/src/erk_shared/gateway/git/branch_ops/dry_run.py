"""No-op Git branch operations wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.gateway.git.abc import BranchDivergence, BranchSyncInfo
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.output.output import user_output


class DryRunGitBranchOps(GitBranchOps):
    """No-op wrapper that prevents execution of branch operations.

    This wrapper intercepts branch operations and either returns without
    executing (for land-stack operations) or prints what would happen.

    Usage:
        real_ops = RealGitBranchOps()
        noop_ops = DryRunGitBranchOps(real_ops)

        # Prints message instead of creating branch
        noop_ops.create_branch(cwd, "feature", "main")
    """

    def __init__(self, wrapped: GitBranchOps) -> None:
        """Create a dry-run wrapper around a GitBranchOps implementation.

        Args:
            wrapped: The GitBranchOps implementation to wrap (usually RealGitBranchOps)
        """
        self._wrapped = wrapped

    def create_branch(self, cwd: Path, branch_name: str, start_point: str, *, force: bool) -> None:
        """Print dry-run message instead of creating branch."""
        force_flag = " -f" if force else ""
        user_output(f"[DRY RUN] Would run: git branch{force_flag} {branch_name} {start_point}")

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Print dry-run message instead of deleting branch."""
        flag = "-D" if force else "-d"
        user_output(f"[DRY RUN] Would run: git branch {flag} {branch_name}")

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """No-op for checkout in dry-run mode."""
        # Do nothing - prevents actual checkout execution
        pass

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """No-op for detached checkout in dry-run mode."""
        # Do nothing - prevents actual detached HEAD checkout execution
        pass

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """No-op for creating tracking branch in dry-run mode."""
        # Do nothing - prevents actual tracking branch creation
        pass

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
