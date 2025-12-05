"""Production GitBranches implementation using subprocess."""

import subprocess
from pathlib import Path

from erk_shared.git.branches.abc import GitBranches
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitBranches(GitBranches):
    """Production implementation using subprocess."""

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        branch = result.stdout.strip()
        if branch == "HEAD":
            return None

        return branch

    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name.

        Checks git's remote HEAD reference, then falls back to checking for
        existence of 'main' then 'master'. Returns 'main' as final fallback
        if neither branch exists.
        """
        # 1. Try git symbolic-ref to detect default branch
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            # Parse "refs/remotes/origin/master" -> "master"
            ref = result.stdout.strip()
            if ref.startswith("refs/remotes/origin/"):
                return ref.replace("refs/remotes/origin/", "")

        # 2. Fallback: try 'main' then 'master', use first that exists
        for candidate in ["main", "master"]:
            result = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{candidate}"],
                cwd=repo_root,
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                return candidate

        # 3. Final fallback: 'main'
        return "main"

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate that a configured trunk branch exists.

        Args:
            repo_root: Path to the repository root
            name: Trunk branch name to validate

        Returns:
            The validated trunk branch name

        Raises:
            RuntimeError: If the specified branch doesn't exist
        """
        result = subprocess.run(
            ["git", "rev-parse", "--verify", name],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return name
        error_msg = (
            f"Error: Configured trunk branch '{name}' does not exist in repository.\n"
            f"Update your configuration in pyproject.toml or create the branch."
        )
        raise RuntimeError(error_msg)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository."""
        result = run_subprocess_with_context(
            ["git", "branch", "--format=%(refname:short)"],
            operation_context="list local branches",
            cwd=repo_root,
        )
        branches = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return branches

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository."""
        result = run_subprocess_with_context(
            ["git", "branch", "-r", "--format=%(refname:short)"],
            operation_context="list remote branches",
            cwd=repo_root,
        )
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote."""
        remote_branches = self.list_remote_branches(repo_root)
        remote_ref = f"{remote}/{branch}"
        return remote_ref in remote_branches

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch."""
        run_subprocess_with_context(
            ["git", "branch", "--track", branch, remote_ref],
            operation_context=f"create tracking branch '{branch}' from '{remote_ref}'",
            cwd=repo_root,
        )

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create a new branch without checking it out."""
        run_subprocess_with_context(
            ["git", "branch", branch_name, start_point],
            operation_context=f"create branch '{branch_name}' from '{start_point}'",
            cwd=cwd,
        )

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch."""
        flag = "-D" if force else "-d"
        run_subprocess_with_context(
            ["git", "branch", flag, branch_name],
            operation_context=f"delete branch '{branch_name}'",
            cwd=cwd,
        )

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Delete a branch using Graphite's gt delete command."""
        cmd = ["gt", "delete", branch]
        if force:
            cmd.insert(2, "-f")
        run_subprocess_with_context(
            cmd,
            operation_context=f"delete branch '{branch}' with Graphite",
            cwd=repo_root,
        )

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        run_subprocess_with_context(
            ["git", "checkout", branch],
            operation_context=f"checkout branch '{branch}'",
            cwd=cwd,
        )

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref."""
        run_subprocess_with_context(
            ["git", "checkout", "--detach", ref],
            operation_context=f"checkout detached HEAD at '{ref}'",
            cwd=cwd,
        )

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch."""
        result = subprocess.run(
            ["git", "rev-parse", branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        return result.stdout.strip()
