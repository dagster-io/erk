"""No-op Git branch operations wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.git.branch_ops.abc import GitBranchOps
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
