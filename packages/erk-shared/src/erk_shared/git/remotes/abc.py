"""Abstract interface for git remote operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitRemotes(ABC):
    """Abstract interface for git remote operations.

    All implementations (real, fake, dry-run) must implement this interface.
    """

    @abstractmethod
    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch a specific branch from a remote."""
        ...

    @abstractmethod
    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull a specific branch from a remote."""
        ...

    @abstractmethod
    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        """Push a branch to a remote."""
        ...

    @abstractmethod
    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote."""
        ...

    @abstractmethod
    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        """Get the URL for a git remote."""
        ...

    @abstractmethod
    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        """Fetch a PR ref into a local branch."""
        ...
