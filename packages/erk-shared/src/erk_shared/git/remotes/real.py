"""Production GitRemotes implementation using subprocess."""

import subprocess
from pathlib import Path

from erk_shared.git.remotes.abc import GitRemotes
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitRemotes(GitRemotes):
    """Production implementation using subprocess."""

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch a specific branch from a remote."""
        run_subprocess_with_context(
            ["git", "fetch", remote, branch],
            operation_context=f"fetch branch '{branch}' from remote '{remote}'",
            cwd=repo_root,
        )

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull a specific branch from a remote."""
        cmd = ["git", "pull"]
        if ff_only:
            cmd.append("--ff-only")
        cmd.extend([remote, branch])

        run_subprocess_with_context(
            cmd,
            operation_context=f"pull branch '{branch}' from remote '{remote}'",
            cwd=repo_root,
        )

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        """Push a branch to a remote."""
        cmd = ["git", "push"]
        if set_upstream:
            cmd.append("-u")
        cmd.extend([remote, branch])

        run_subprocess_with_context(
            cmd,
            operation_context=f"push branch '{branch}' to remote '{remote}'",
            cwd=cwd,
        )

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote."""
        result = subprocess.run(
            ["git", "ls-remote", remote, branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        """Get the URL for a git remote.

        Raises:
            ValueError: If remote doesn't exist or has no URL
        """
        result = subprocess.run(
            ["git", "remote", "get-url", remote],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(f"Remote '{remote}' not found in repository")
        url = result.stdout.strip()
        if not url:
            raise ValueError(f"Remote '{remote}' has no URL configured")
        return url

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        """Fetch a PR ref into a local branch.

        Uses GitHub's special refs/pull/<number>/head reference.
        """
        run_subprocess_with_context(
            ["git", "fetch", remote, f"pull/{pr_number}/head:{local_branch}"],
            operation_context=f"fetch PR #{pr_number} into branch '{local_branch}'",
            cwd=repo_root,
        )
