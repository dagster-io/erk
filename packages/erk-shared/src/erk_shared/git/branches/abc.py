"""Abstract interface for git branch operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitBranches(ABC):
    """Abstract interface for git branch operations.

    All implementations (real, fake, dry-run) must implement this interface.
    """

    @abstractmethod
    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch.

        Returns None if in detached HEAD state.
        """
        ...

    @abstractmethod
    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name (main/master).

        Raises RuntimeError if neither main nor master exists.
        """
        ...

    @abstractmethod
    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate that a configured trunk branch exists.

        Raises RuntimeError if the branch doesn't exist.
        """
        ...

    @abstractmethod
    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names."""
        ...

    @abstractmethod
    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names (e.g., 'origin/main')."""
        ...

    @abstractmethod
    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote.

        Args:
            repo_root: Repository root directory
            remote: Remote name (e.g., 'origin')
            branch: Branch name (e.g., 'feature-branch')

        Returns:
            True if the branch exists on the remote, False otherwise
        """
        ...

    @abstractmethod
    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch."""
        ...

    @abstractmethod
    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create a new branch without checking it out."""
        ...

    @abstractmethod
    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch."""
        ...

    @abstractmethod
    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Delete a branch using Graphite's gt delete command."""
        ...

    @abstractmethod
    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        ...

    @abstractmethod
    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref."""
        ...

    @abstractmethod
    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch.

        Returns None if the branch doesn't exist.
        """
        ...
