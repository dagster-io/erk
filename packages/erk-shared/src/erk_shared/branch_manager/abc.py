"""Abstract base class for BranchManager operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.branch_manager.types import PrInfo


class BranchManager(ABC):
    """Dual-mode interface for branch operations.

    Provides consistent interface regardless of whether
    Graphite or plain Git is being used. This abstraction
    allows the statusline (and other consumers) to work
    transparently with both Graphite-managed and plain Git
    repositories.

    Key operations:
    - get_pr_for_branch: Get PR info from Graphite cache (fast) or GitHub API (fallback)
    - create_branch: Create branch via gt create (Graphite) or git branch (Git)
    """

    @abstractmethod
    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PrInfo | None:
        """Get PR info for a branch.

        For Graphite: Reads from .graphite_pr_info cache (fast, no network).
        For Git: Calls GitHub REST API to look up PR by branch name.

        Args:
            repo_root: Repository root directory
            branch: Branch name to look up

        Returns:
            PrInfo if a PR exists for the branch, None otherwise.
        """
        ...

    @abstractmethod
    def create_branch(self, repo_root: Path, branch_name: str, base_branch: str) -> None:
        """Create a new branch from base.

        For Graphite: Uses `gt create` to create and track the branch.
        For Git: Uses `git branch` to create the branch.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the new branch
            base_branch: Name of the parent/base branch
        """
        ...

    @abstractmethod
    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Delete a local branch.

        For Graphite: Uses `git branch -D` with Graphite metadata cleanup.
        For Git: Uses plain `git branch -D`.

        Args:
            repo_root: Repository root directory
            branch: Branch name to delete
        """
        ...

    @abstractmethod
    def submit_branch(self, repo_root: Path, branch: str) -> None:
        """Submit a branch to remote.

        For Graphite: Uses `gt submit --force --quiet` to submit the stack.
        For Git: Uses `git push -u origin <branch>` to push with upstream tracking.

        Args:
            repo_root: Repository root directory
            branch: Branch name to submit
        """
        ...

    @abstractmethod
    def get_branch_stack(self, repo_root: Path, branch: str) -> list[str] | None:
        """Get the linear worktree stack for a given branch.

        For Graphite: Returns the stack from trunk to leaf containing this branch.
        For Git: Returns None (stacks are a Graphite-only feature).

        Args:
            repo_root: Repository root directory
            branch: Name of the branch to get the stack for

        Returns:
            List of branch names in the stack (ordered trunk to leaf),
            or None if branch is not tracked/stacks unavailable.
        """
        ...

    @abstractmethod
    def is_graphite_managed(self) -> bool:
        """Returns True if using Graphite for branch operations.

        This allows consumers to show different UI or behavior
        depending on whether Graphite is available.
        """
        ...
