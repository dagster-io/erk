"""Abstract base class for GitHub repository operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.github.types import RepoInfo


class GitHubRepoGateway(ABC):
    """Abstract interface for GitHub repository operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def get_repo_info(self, repo_root: Path) -> RepoInfo:
        """Get repository owner and name from GitHub CLI.

        Args:
            repo_root: Repository root directory

        Returns:
            RepoInfo with owner and name

        Raises:
            RuntimeError: If gh command fails
        """
        ...
