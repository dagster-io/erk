"""Abstract base class for Git commit operations.

This sub-gateway extracts commit operations from the main Git gateway,
including staging, committing, amending, and commit message queries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GitCommitOps(ABC):
    """Abstract interface for Git commit operations.

    This interface contains both mutation and query operations for commits.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    @abstractmethod
    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Stage specific files for commit.

        Args:
            cwd: Working directory
            paths: List of file paths to stage (relative to cwd)

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def commit(self, cwd: Path, message: str) -> None:
        """Create a commit with staged changes.

        Always uses --allow-empty to support creating commits even with no staged changes.

        Args:
            cwd: Working directory
            message: Commit message

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def add_all(self, cwd: Path) -> None:
        """Stage all changes for commit (git add -A).

        Args:
            cwd: Working directory

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def amend_commit(self, cwd: Path, message: str) -> None:
        """Amend the current commit with a new message.

        Args:
            cwd: Working directory
            message: New commit message

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get the commit message for a given commit SHA.

        Args:
            repo_root: Path to the git repository root
            commit_sha: Commit SHA to query

        Returns:
            First line of commit message, or None if commit doesn't exist.
        """
        ...

    @abstractmethod
    def get_commit_messages_since(self, cwd: Path, base_branch: str) -> list[str]:
        """Get full commit messages for commits in HEAD but not in base_branch.

        Returns commits in chronological order (oldest first).

        Args:
            cwd: Working directory
            base_branch: Branch to compare against (e.g., parent branch)

        Returns:
            List of full commit messages (subject + body) for each unique commit
        """
        ...

    @abstractmethod
    def get_head_commit_message_full(self, cwd: Path) -> str:
        """Get the full commit message (subject + body) of HEAD commit.

        Uses git log -1 --format=%B HEAD to get the complete message.

        Args:
            cwd: Working directory

        Returns:
            Full commit message including subject and body
        """
        ...

    @abstractmethod
    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commit information.

        Args:
            cwd: Working directory
            limit: Maximum number of commits to retrieve

        Returns:
            List of commit info dicts with keys: sha, message, author, date
        """
        ...
