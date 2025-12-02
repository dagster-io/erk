"""Abstract operations interfaces for GT kit subprocess commands.

This module defines ABC interfaces for Graphite (gt) and GitHub (gh) operations
used by GT kit CLI commands. These interfaces enable dependency injection with
in-memory fakes for testing while maintaining type safety.

Design:
- GitHubGtKit for GitHub operations
- Composite GtKit interface that combines Git, GitHubGtKit, and main_graphite()
- Return values match existing subprocess patterns (str | None, bool, etc.)
- LBYL pattern: operations check state, return None/False on failure

Note: Git operations are provided by the core Git interface from erk_shared.git.abc.
"""

from abc import ABC, abstractmethod

from erk_shared.git.abc import Git
from erk_shared.integrations.graphite.abc import Graphite


class GitHubGtKit(ABC):
    """GitHub (gh) operations interface for GT kit commands."""

    @abstractmethod
    def get_pr_info(self) -> tuple[int, str] | None:
        """Get PR number and URL for current branch.

        Returns:
            Tuple of (number, url) or None if no PR exists
        """

    @abstractmethod
    def get_pr_state(self) -> tuple[int, str] | None:
        """Get PR number and state for current branch.

        Returns:
            Tuple of (number, state) or None if no PR exists
        """

    @abstractmethod
    def update_pr_metadata(self, title: str, body: str) -> bool:
        """Update PR title and body using gh pr edit.

        Args:
            title: New PR title
            body: New PR body

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def mark_pr_ready(self) -> bool:
        """Mark PR as ready for review using gh pr ready.

        Converts a draft PR to ready status. If PR is already ready, this is a no-op.

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def get_pr_title(self) -> str | None:
        """Get the title of the PR for the current branch.

        Returns:
            PR title string, or None if no PR exists
        """

    @abstractmethod
    def get_pr_body(self) -> str | None:
        """Get the body of the PR for the current branch.

        Returns:
            PR body string, or None if no PR exists
        """

    @abstractmethod
    def merge_pr(self, *, subject: str | None = None, body: str | None = None) -> bool:
        """Merge the PR using squash merge.

        Args:
            subject: Optional commit message subject for squash merge.
                     If provided, overrides GitHub's default behavior.
            body: Optional commit message body for squash merge.
                  If provided, included as the commit body text.

        Returns:
            True on success, False on failure
        """

    @abstractmethod
    def get_graphite_pr_url(self, pr_number: int) -> str | None:
        """Get Graphite PR URL for given PR number.

        Args:
            pr_number: PR number

        Returns:
            Graphite URL or None if repo info cannot be determined
        """

    @abstractmethod
    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status.

        Returns:
            Tuple of (is_authenticated, username, hostname):
            - is_authenticated: True if gh CLI is authenticated
            - username: Authenticated username or None
            - hostname: GitHub hostname or None
        """

    @abstractmethod
    def get_pr_diff(self, pr_number: int) -> str:
        """Get the diff for a PR using gh pr diff.

        Args:
            pr_number: PR number to get diff for

        Returns:
            Diff content as string

        Raises:
            subprocess.CalledProcessError: If gh command fails
        """

    @abstractmethod
    def get_pr_status(self, branch: str) -> tuple[int | None, str | None]:
        """Get PR number and URL for a specific branch.

        Args:
            branch: Branch name to check

        Returns:
            Tuple of (pr_number, pr_url) or (None, None) if no PR exists
        """

    @abstractmethod
    def get_pr_mergeability(self, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status from GitHub API.

        Args:
            pr_number: PR number to check

        Returns:
            Tuple of (mergeable, merge_state_status):
            - mergeable: "MERGEABLE", "CONFLICTING", or "UNKNOWN"
            - merge_state_status: "CLEAN", "DIRTY", "UNSTABLE", etc.
        """


class GtKit(ABC):
    """Composite interface combining all GT kit operations.

    This interface provides a single injection point for all git, Graphite,
    and GitHub operations used by GT kit CLI commands.
    """

    @abstractmethod
    def git(self) -> Git:
        """Get the git operations interface.

        Returns:
            Git implementation
        """

    @abstractmethod
    def github(self) -> GitHubGtKit:
        """Get the GitHub operations interface.

        Returns:
            GitHubGtKitOps implementation
        """

    @abstractmethod
    def main_graphite(self) -> Graphite:
        """Get the main Graphite operations interface.

        Returns:
            Graphite implementation for full graphite operations
        """
