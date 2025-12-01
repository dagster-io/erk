"""Abstract operations interfaces for GT kit subprocess commands.

This module defines ABC interfaces for git and Graphite (gt) operations
used by GT kit CLI commands. These interfaces enable dependency injection with
in-memory fakes for testing while maintaining type safety.

Design:
- GitGtKit for git operations specific to GT kit commands
- GtKit composite interface that combines GitGtKit + GitHub (unified) + Graphite
- GitHub operations use the unified GitHub ABC from erk_shared.github.abc
- Return values match existing subprocess patterns (str | None, bool, etc.)
- LBYL pattern: operations check state, return None/False on failure
"""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.integrations.graphite.abc import Graphite


class GitGtKit(ABC):
    """Git operations interface for GT kit commands."""

    @abstractmethod
    def get_current_branch(self) -> str | None:
        """Get the name of the current branch.

        Returns:
            Branch name or None if command fails
        """

    @abstractmethod
    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes.

        Returns:
            True if changes exist, False otherwise
        """

    @abstractmethod
    def add_all(self) -> bool:
        """Stage all changes for commit.

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def commit(self, message: str) -> bool:
        """Create a commit with the given message.

        Args:
            message: Commit message

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def amend_commit(self, message: str) -> bool:
        """Amend the current commit with a new message.

        Args:
            message: New commit message

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def count_commits_in_branch(self, parent_branch: str) -> int:
        """Count commits in current branch compared to parent.

        Args:
            parent_branch: Name of the parent branch

        Returns:
            Number of commits, 0 if command fails
        """

    @abstractmethod
    def get_trunk_branch(self) -> str:
        """Get the trunk branch name for the repository.

        Detects the trunk branch by checking git's remote HEAD reference,
        falling back to common trunk branch names if detection fails.

        Returns:
            Trunk branch name (e.g., 'main', 'master')
        """

    @abstractmethod
    def get_repository_root(self) -> str:
        """Get the absolute path to the repository root.

        Returns:
            Absolute path to repo root

        Raises:
            subprocess.CalledProcessError: If not in a git repository
        """

    @abstractmethod
    def get_diff_to_parent(self, parent_branch: str) -> str:
        """Get git diff between parent branch and HEAD.

        Args:
            parent_branch: Name of the parent branch

        Returns:
            Full diff output as string

        Raises:
            subprocess.CalledProcessError: If diff command fails
        """

    @abstractmethod
    def check_merge_conflicts(self, base_branch: str, head_branch: str) -> bool:
        """Check if merging head_branch into base_branch would have conflicts.

        Uses git merge-tree to simulate merge without touching working tree.

        Args:
            base_branch: Base branch name (e.g., "master", "main")
            head_branch: Head branch name (current branch)

        Returns:
            True if conflicts detected, False otherwise
        """

    @abstractmethod
    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory for a path.

        For regular repos, this is the .git directory.
        For worktrees, this is the shared .git directory (not the worktree's .git file).

        Args:
            cwd: Path within the repository

        Returns:
            Path to the common git directory, or None if not in a git repo
        """

    @abstractmethod
    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch.

        Args:
            repo_root: Repository root directory
            branch: Branch name

        Returns:
            Commit SHA or None if branch doesn't exist
        """

    @abstractmethod
    def checkout_branch(self, branch: str) -> bool:
        """Switch to a different branch.

        Args:
            branch: Branch name to checkout

        Returns:
            True on success, False on failure
        """


class GtKit(ABC):
    """Composite interface combining all GT kit operations.

    This interface provides a single injection point for all git, Graphite,
    and GitHub operations used by GT kit CLI commands.
    """

    @abstractmethod
    def git(self) -> GitGtKit:
        """Get the git operations interface.

        Returns:
            GitGtKit implementation
        """

    @abstractmethod
    def github(self) -> GitHub:
        """Get the unified GitHub operations interface.

        Returns:
            GitHub implementation from erk_shared.github.abc
        """

    @abstractmethod
    def main_graphite(self) -> Graphite:
        """Get the main Graphite operations interface.

        Returns:
            Graphite implementation for full graphite operations
        """
