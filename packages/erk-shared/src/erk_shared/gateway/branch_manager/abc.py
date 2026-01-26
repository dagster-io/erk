"""Abstract base class for BranchManager operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.gateway.branch_manager.types import PrInfo


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
    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        """Delete a local branch.

        For Graphite: Uses `git branch -D` with Graphite metadata cleanup.
        For Git: Uses plain `git branch -D`.

        Args:
            repo_root: Repository root directory
            branch: Branch name to delete
            force: If True, use -D (force delete) instead of -d
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
    def commit(self, repo_root: Path, message: str) -> None:
        """Create a commit on the current branch.

        For both Graphite and Git: Uses `git commit --allow-empty` since
        commits are not Graphite-specific operations.

        Args:
            repo_root: Repository root directory
            message: Commit message
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
    def track_branch(self, repo_root: Path, branch_name: str, parent_branch: str) -> None:
        """Track an existing branch with parent relationship.

        For Graphite: Registers the branch with Graphite for stack tracking.
        For Git: No-op (plain Git doesn't track parent relationships).

        This is useful when a branch was created via git directly and needs
        to be registered with Graphite separately.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the branch to track
            parent_branch: Name of the parent branch
        """
        ...

    @abstractmethod
    def get_parent_branch(self, repo_root: Path, branch: str) -> str | None:
        """Get parent branch name for a given branch.

        For Graphite: Returns the parent branch from Graphite's cache.
        For Git: Returns None (plain Git doesn't track parent relationships).

        Args:
            repo_root: Repository root directory
            branch: Name of the branch to get the parent for

        Returns:
            Parent branch name, or None if:
            - Branch is not tracked (Graphite mode)
            - Branch has no parent (is trunk)
            - Parent relationships not tracked (Git mode)
        """
        ...

    @abstractmethod
    def get_child_branches(self, repo_root: Path, branch: str) -> list[str]:
        """Get child branch names for a given branch.

        For Graphite: Returns children from Graphite's cache.
        For Git: Returns empty list (plain Git doesn't track children).

        Args:
            repo_root: Repository root directory
            branch: Name of the branch to get children for

        Returns:
            List of child branch names, or empty list if:
            - Branch is not tracked (Graphite mode)
            - Branch has no children
            - Child relationships not tracked (Git mode)
        """
        ...

    @abstractmethod
    def checkout_branch(self, repo_root: Path, branch: str) -> None:
        """Checkout a branch in the given directory.

        Args:
            repo_root: Repository root directory
            branch: Branch name to checkout

        Raises:
            RuntimeError: If the branch is already checked out in another worktree
        """
        ...

    @abstractmethod
    def checkout_detached(self, repo_root: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref.

        Args:
            repo_root: Repository root directory
            ref: Git ref to checkout (commit SHA, branch name, etc.)
        """
        ...

    @abstractmethod
    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch.

        Args:
            repo_root: Repository root directory
            branch: Name for the local branch
            remote_ref: Remote reference to track (e.g., 'origin/feature-remote')
        """
        ...

    @abstractmethod
    def is_graphite_managed(self) -> bool:
        """Returns True if using Graphite for branch operations.

        This allows consumers to show different UI or behavior
        depending on whether Graphite is available.
        """
        ...
