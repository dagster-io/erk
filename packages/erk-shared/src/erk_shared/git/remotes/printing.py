"""Printing GitRemotes wrapper for verbose output."""

from pathlib import Path

from erk_shared.git.remotes.abc import GitRemotes
from erk_shared.printing.base import PrintingBase


class PrintingGitRemotes(PrintingBase, GitRemotes):
    """Wrapper that prints operations before delegating."""

    # Read-only: delegate without printing
    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        return self._wrapped.branch_exists_on_remote(repo_root, remote, branch)

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        return self._wrapped.get_remote_url(repo_root, remote)

    # Write operations: print then delegate
    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        self._emit(self._format_command(f"git fetch {remote} {branch}"))
        self._wrapped.fetch_branch(repo_root, remote, branch)

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        ff_flag = " --ff-only" if ff_only else ""
        self._emit(self._format_command(f"git pull{ff_flag} {remote} {branch}"))
        self._wrapped.pull_branch(repo_root, remote, branch, ff_only=ff_only)

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        upstream_flag = "-u " if set_upstream else ""
        self._emit(self._format_command(f"git push {upstream_flag}{remote} {branch}"))
        self._wrapped.push_to_remote(cwd, remote, branch, set_upstream=set_upstream)

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        self._emit(self._format_command(f"git fetch {remote} pull/{pr_number}/head:{local_branch}"))
        self._wrapped.fetch_pr_ref(repo_root, remote, pr_number, local_branch)
