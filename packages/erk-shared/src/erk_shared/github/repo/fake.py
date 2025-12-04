"""Fake GitHub repository operations for testing."""

from pathlib import Path

from erk_shared.github.repo.abc import GitHubRepoGateway
from erk_shared.github.types import RepoInfo


class FakeGitHubRepoGateway(GitHubRepoGateway):
    """In-memory fake implementation of GitHub repository operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults.
    """

    def __init__(
        self,
        *,
        owner: str = "test-owner",
        name: str = "test-repo",
    ) -> None:
        """Create FakeGitHubRepoGateway with pre-configured state.

        Args:
            owner: Repository owner to return (default: "test-owner")
            name: Repository name to return (default: "test-repo")
        """
        self._owner = owner
        self._name = name

    def get_repo_info(self, repo_root: Path) -> RepoInfo:
        """Get repository owner and name (returns pre-configured defaults)."""
        return RepoInfo(owner=self._owner, name=self._name)
