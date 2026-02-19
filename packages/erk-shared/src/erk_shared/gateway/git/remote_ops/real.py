"""Production implementation of Git remote operations using subprocess."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.lock import wait_for_index_lock
from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.gateway.git.remote_ops.types import (
    PullRebaseError,
    PullRebaseResult,
    PushError,
    PushResult,
)
from erk_shared.gateway.time.abc import Time
from erk_shared.subprocess_utils import copied_env_for_git_subprocess, run_subprocess_with_context

# Timeout in seconds for network-touching git operations (push, pull, fetch).
# Prevents indefinite hangs on network issues or credential prompts.
_GIT_NETWORK_TIMEOUT = 120


class RealGitRemoteOps(GitRemoteOps):
    """Real implementation of Git remote operations using subprocess."""

    def __init__(self, time: Time) -> None:
        """Initialize RealGitRemoteOps with Time provider.

        Args:
            time: Time provider for lock waiting
        """
        self._time = time

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch a specific branch from a remote."""
        run_subprocess_with_context(
            cmd=["git", "fetch", remote, branch],
            operation_context=f"fetch branch '{branch}' from remote '{remote}'",
            cwd=repo_root,
            timeout=_GIT_NETWORK_TIMEOUT,
            env=copied_env_for_git_subprocess(),
        )

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull a specific branch from a remote."""
        # Wait for index lock if another git operation is in progress
        wait_for_index_lock(repo_root, self._time)

        cmd = ["git", "pull"]
        if ff_only:
            cmd.append("--ff-only")
        cmd.extend([remote, branch])

        run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"pull branch '{branch}' from remote '{remote}'",
            cwd=repo_root,
            timeout=_GIT_NETWORK_TIMEOUT,
            env=copied_env_for_git_subprocess(),
        )

    def fetch_pr_ref(
        self, *, repo_root: Path, remote: str, pr_number: int, local_branch: str
    ) -> None:
        """Fetch a PR ref into a local branch.

        Uses GitHub's special refs/pull/<number>/head reference.
        """
        run_subprocess_with_context(
            cmd=["git", "fetch", remote, f"pull/{pr_number}/head:{local_branch}"],
            operation_context=f"fetch PR #{pr_number} into branch '{local_branch}'",
            cwd=repo_root,
            timeout=_GIT_NETWORK_TIMEOUT,
            env=copied_env_for_git_subprocess(),
        )

    def push_to_remote(
        self,
        cwd: Path,
        remote: str,
        branch: str,
        *,
        set_upstream: bool,
        force: bool,
    ) -> PushResult | PushError:
        """Push a branch to a remote."""
        cmd = ["git", "push"]
        if set_upstream:
            cmd.append("-u")
        if force:
            cmd.append("--force")
        cmd.extend([remote, branch])

        try:
            run_subprocess_with_context(
                cmd=cmd,
                operation_context=f"push branch '{branch}' to remote '{remote}'",
                cwd=cwd,
                timeout=_GIT_NETWORK_TIMEOUT,
                env=copied_env_for_git_subprocess(),
            )
        except RuntimeError as e:
            return PushError(message=str(e))
        return PushResult()

    def pull_rebase(
        self, cwd: Path, remote: str, branch: str
    ) -> PullRebaseResult | PullRebaseError:
        """Pull and rebase from remote branch."""
        try:
            run_subprocess_with_context(
                cmd=["git", "pull", "--rebase", remote, branch],
                operation_context=f"pull --rebase {remote} {branch}",
                cwd=cwd,
                timeout=_GIT_NETWORK_TIMEOUT,
                env=copied_env_for_git_subprocess(),
            )
        except RuntimeError as e:
            return PullRebaseError(message=str(e))
        return PullRebaseResult()

    def get_remote_url(self, repo_root: Path, remote: str) -> str:
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
