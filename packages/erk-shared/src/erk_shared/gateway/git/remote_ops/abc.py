"""Abstract base class for Git remote operations.

This sub-gateway extracts remote operations from the main Git gateway,
including fetch, pull, and push operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GitRemoteOps(ABC):
    """Abstract interface for Git remote operations.

    This interface contains both mutation and query operations for remotes.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    @abstractmethod
    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch a specific branch from a remote.

        Args:
            repo_root: Path to the git repository root
            remote: Remote name (e.g., "origin")
            branch: Branch name to fetch
        """
        ...

    @abstractmethod
    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull a specific branch from a remote.

        Args:
            repo_root: Path to the git repository root
            remote: Remote name (e.g., "origin")
            branch: Branch name to pull
            ff_only: If True, use --ff-only to prevent merge commits
        """
        ...

    @abstractmethod
    def fetch_pr_ref(
        self, *, repo_root: Path, remote: str, pr_number: int, local_branch: str
    ) -> None:
        """Fetch a PR ref into a local branch.

        Uses GitHub's special refs/pull/<number>/head reference to fetch
        the PR head commit and create a local branch tracking it.

        Command: git fetch <remote> pull/<number>/head:<local_branch>

        Args:
            repo_root: Path to the git repository root
            remote: Remote name (e.g., "origin")
            pr_number: GitHub PR number
            local_branch: Name for the local branch to create

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def push_to_remote(
        self,
        cwd: Path,
        remote: str,
        branch: str,
        *,
        set_upstream: bool = False,
        force: bool = False,
    ) -> None:
        """Push a branch to a remote.

        Args:
            cwd: Working directory
            remote: Remote name (e.g., "origin")
            branch: Branch name to push
            set_upstream: If True, set upstream tracking (-u flag)
            force: If True, force push (--force flag)

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def pull_rebase(self, cwd: Path, remote: str, branch: str) -> None:
        """Pull and rebase from a remote branch.

        Runs `git pull --rebase <remote> <branch>` to fetch remote changes
        and rebase local commits on top of them. This is useful for integrating
        CI commits or other remote changes before pushing.

        Args:
            cwd: Working directory (must be in a git repository)
            remote: Remote name (e.g., "origin")
            branch: Branch name to pull from

        Raises:
            subprocess.CalledProcessError: If rebase fails (e.g., conflicts)
        """
        ...

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        """Get the URL for a git remote.

        Args:
            repo_root: Path to the repository root
            remote: Remote name (defaults to "origin")

        Returns:
            Remote URL as a string

        Raises:
            ValueError: If remote doesn't exist or has no URL
        """
        ...
