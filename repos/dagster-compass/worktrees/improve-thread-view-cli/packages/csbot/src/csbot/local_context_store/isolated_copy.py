from pathlib import Path
from typing import TYPE_CHECKING

from csbot.local_context_store.github.api import create_and_merge_pull_request, create_pull_request

from .git.repository_operations import commit_and_push_changes

if TYPE_CHECKING:
    from csbot.local_context_store.github.config import GithubConfig


class IsolatedContextStoreCopy:
    """Handle to isolated context store for PR workflows."""

    def __init__(self, temp_repo_path: Path, github_config: "GithubConfig"):
        self.temp_repo_path = temp_repo_path
        self.github_config = github_config

    def commit_changes(self, message: str, author_name: str, author_email: str) -> str:
        """Commit and push changes (no locking needed for isolated context store).

        Args:
            message: Commit message
            author_name: Name of the commit author
            author_email: Email of the commit author

        Returns:
            str: Name of the branch that was pushed
        """
        return commit_and_push_changes(
            self.temp_repo_path,
            message,
            github_config=self.github_config,
            author_name=author_name,
            author_email=author_email,
        )

    # PR-specific operations
    def create_pull_request(self, title: str, body: str, branch: str) -> str:
        """Create a pull request.

        Args:
            title: PR title
            body: PR description
            branch: Branch name for the PR

        Returns:
            str: URL of the created pull request
        """
        return create_pull_request(self.github_config, title, body, branch)

    def create_and_merge_pull_request(self, title: str, body: str, branch: str) -> str:
        """Create and immediately merge a pull request.

        Args:
            title: PR title
            body: PR description
            branch: Branch name for the PR

        Returns:
            str: URL of the merged pull request
        """
        return create_and_merge_pull_request(self.github_config, title, body, branch)
