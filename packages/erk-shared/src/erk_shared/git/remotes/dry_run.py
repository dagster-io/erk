"""No-op GitRemotes wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.git.remotes.abc import GitRemotes


class DryRunGitRemotes(GitRemotes):
    """No-op wrapper that prevents execution of remote operations."""

    def __init__(self, wrapped: GitRemotes) -> None:
        self._wrapped = wrapped

    # Read-only: delegate
    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        # Return True to allow dry-run to continue
        return True

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        return self._wrapped.get_remote_url(repo_root, remote)

    # Write operations: no-op
    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        pass  # No-op

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        pass  # No-op

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        pass  # No-op

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        pass  # No-op
