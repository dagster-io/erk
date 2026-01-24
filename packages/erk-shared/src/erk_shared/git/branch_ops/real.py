"""Production implementation of Git branch operations using subprocess."""

from pathlib import Path

from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime
from erk_shared.git.branch_ops.abc import GitBranchOps
from erk_shared.git.lock import wait_for_index_lock
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitBranchOps(GitBranchOps):
    """Production implementation of branch operations using subprocess.

    All git operations execute actual git commands via subprocess.
    """

    def __init__(self, time: Time | None = None) -> None:
        """Initialize RealGitBranchOps with optional Time provider.

        Args:
            time: Time provider for lock waiting. Defaults to RealTime().
        """
        self._time = time if time is not None else RealTime()

    def create_branch(self, cwd: Path, branch_name: str, start_point: str, *, force: bool) -> None:
        """Create a new branch without checking it out."""
        cmd = ["git", "branch"]
        if force:
            cmd.append("-f")
        cmd.extend([branch_name, start_point])
        run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"create branch '{branch_name}' from '{start_point}'",
            cwd=cwd,
        )

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch."""
        flag = "-D" if force else "-d"
        run_subprocess_with_context(
            cmd=["git", "branch", flag, branch_name],
            operation_context=f"delete branch '{branch_name}'",
            cwd=cwd,
        )

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        # Wait for index lock if another git operation is in progress
        wait_for_index_lock(cwd, self._time)

        run_subprocess_with_context(
            cmd=["git", "checkout", branch],
            operation_context=f"checkout branch '{branch}'",
            cwd=cwd,
        )

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref."""
        run_subprocess_with_context(
            cmd=["git", "checkout", "--detach", ref],
            operation_context=f"checkout detached HEAD at '{ref}'",
            cwd=cwd,
        )

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch."""
        run_subprocess_with_context(
            cmd=["git", "branch", "--track", branch, remote_ref],
            operation_context=f"create tracking branch '{branch}' from '{remote_ref}'",
            cwd=repo_root,
        )
