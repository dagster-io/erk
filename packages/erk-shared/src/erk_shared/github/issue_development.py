"""Abstract interface for issue-linked branch development operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DevelopmentBranch:
    """Result of creating or getting an issue-linked development branch.

    Attributes:
        branch_name: The branch name (e.g., "123-my-feature")
        issue_number: The GitHub issue number this branch is linked to
        already_existed: True if the branch already existed, False if newly created
    """

    branch_name: str
    issue_number: int
    already_existed: bool


class IssueDevelopment(ABC):
    """Abstract interface for issue-linked branch operations.

    This interface wraps `gh issue develop` which creates branches that are
    automatically linked to GitHub issues, appearing in the issue sidebar
    under "Development".

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def create_development_branch(
        self,
        repo_root: Path,
        issue_number: int,
        *,
        base_branch: str | None = None,
    ) -> DevelopmentBranch:
        """Create a development branch linked to an issue via gh issue develop.

        If a development branch already exists for the issue, returns that
        branch name with already_existed=True.

        Args:
            repo_root: Repository root directory
            issue_number: GitHub issue number to link the branch to
            base_branch: Optional base branch to create from (defaults to repo default)

        Returns:
            DevelopmentBranch with branch name and creation status

        Raises:
            RuntimeError: If gh CLI fails (not installed, not authenticated, or command error)
        """
        ...

    @abstractmethod
    def get_linked_branch(
        self,
        repo_root: Path,
        issue_number: int,
    ) -> str | None:
        """Get existing development branch linked to an issue.

        Args:
            repo_root: Repository root directory
            issue_number: GitHub issue number to check

        Returns:
            Branch name if a linked branch exists, None otherwise

        Raises:
            RuntimeError: If gh CLI fails (not installed, not authenticated, or command error)
        """
        ...
