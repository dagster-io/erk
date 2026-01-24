"""Abstract base class for Git branch operations.

This sub-gateway extracts branch mutation operations from the main Git gateway,
making BranchManager the enforced abstraction for branch mutations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GitBranchOps(ABC):
    """Abstract interface for Git branch mutation operations.

    This interface contains ONLY mutation operations that modify branch state.
    Query operations (get_current_branch, list_local_branches, etc.) remain
    on the main Git ABC for convenience.

    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    @abstractmethod
    def create_branch(self, cwd: Path, branch_name: str, start_point: str, *, force: bool) -> None:
        """Create a new branch without checking it out.

        Args:
            cwd: Working directory to run command in
            branch_name: Name of the branch to create
            start_point: Commit/branch to base the new branch on
            force: Use -f flag to move existing branch to the start_point
        """
        ...

    @abstractmethod
    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch.

        Args:
            cwd: Working directory to run command in
            branch_name: Name of the branch to delete
            force: Use -D (force delete) instead of -d
        """
        ...

    @abstractmethod
    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory.

        Args:
            cwd: Working directory to run command in
            branch: Branch name to checkout
        """
        ...

    @abstractmethod
    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref.

        Args:
            cwd: Working directory to run command in
            ref: Git ref to checkout (commit SHA, branch name, etc.)
        """
        ...

    @abstractmethod
    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch.

        Args:
            repo_root: Path to the repository root
            branch: Name for the local branch (e.g., 'feature-remote')
            remote_ref: Remote reference to track (e.g., 'origin/feature-remote')

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...
