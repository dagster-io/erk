"""Abstract interface for GitHub issue operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.github.issues.types import (
    CreateIssueResult,
    IssueComment,
    IssueInfo,
    PRReference,
)


class GitHubIssues(ABC):
    """Abstract interface for GitHub issue operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def create_issue(
        self, *, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """Create a new GitHub issue.

        Args:
            repo_root: Repository root directory
            title: Issue title
            body: Issue body markdown
            labels: List of label names to apply

        Returns:
            CreateIssueResult with issue number and full GitHub URL

        Raises:
            RuntimeError: If gh CLI fails (not installed, not authenticated, or command error)
        """
        ...

    @abstractmethod
    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Fetch issue data by number.

        Args:
            repo_root: Repository root directory
            number: Issue number to fetch

        Returns:
            IssueInfo with title, body, state, and url

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def add_comment(self, repo_root: Path, number: int, body: str) -> int:
        """Add a comment to an existing issue.

        Args:
            repo_root: Repository root directory
            number: Issue number to comment on
            body: Comment body markdown

        Returns:
            The comment ID of the newly created comment

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def update_issue_body(self, repo_root: Path, number: int, body: str) -> None:
        """Update the body of an existing issue.

        Args:
            repo_root: Repository root directory
            number: Issue number to update
            body: New issue body markdown

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def list_issues(
        self,
        *,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[IssueInfo]:
        """Query issues by criteria.

        Args:
            repo_root: Repository root directory
            labels: Filter by labels (all labels must match)
            state: Filter by state ("open", "closed", or "all")
            limit: Maximum number of issues to return (None = no limit)

        Returns:
            List of IssueInfo matching the criteria

        Raises:
            RuntimeError: If gh CLI fails
        """
        ...

    @abstractmethod
    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        """Fetch all comment bodies for an issue.

        Args:
            repo_root: Path to repository root
            number: Issue number

        Returns:
            List of comment bodies (markdown strings)

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def get_comment_by_id(self, repo_root: Path, comment_id: int) -> str:
        """Fetch a single comment body by its ID.

        Args:
            repo_root: Path to repository root
            comment_id: Comment ID from GitHub

        Returns:
            Comment body as markdown string

        Raises:
            RuntimeError: If gh CLI fails or comment not found
        """
        ...

    @abstractmethod
    def get_issue_comments_with_urls(self, repo_root: Path, number: int) -> list[IssueComment]:
        """Fetch all comments with their URLs for an issue.

        Args:
            repo_root: Path to repository root
            number: Issue number

        Returns:
            List of IssueComment objects with body and url

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def ensure_label_exists(
        self, *, repo_root: Path, label: str, description: str, color: str
    ) -> None:
        """Ensure a label exists in the repository, creating it if needed.

        Args:
            repo_root: Repository root directory
            label: Label name to ensure exists
            description: Label description (used if creating)
            color: Label color hex code without '#' (used if creating)

        Raises:
            RuntimeError: If gh CLI fails (not installed, not authenticated, or command error)
        """
        ...

    @abstractmethod
    def label_exists(self, repo_root: Path, label: str) -> bool:
        """Check if a label exists in the repository (read-only).

        Args:
            repo_root: Repository root directory
            label: Label name to check

        Returns:
            True if label exists, False otherwise

        Raises:
            RuntimeError: If gh CLI fails (not installed, not authenticated, or command error)
        """
        ...

    @abstractmethod
    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Ensure a label is present on an existing issue (idempotent).

        Args:
            repo_root: Repository root directory
            issue_number: Issue number to ensure label on
            label: Label name to ensure is present

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def remove_label_from_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Remove a label from an existing issue.

        Args:
            repo_root: Repository root directory
            issue_number: Issue number to remove label from
            label: Label name to remove

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def close_issue(self, repo_root: Path, number: int) -> None:
        """Close a GitHub issue.

        Args:
            repo_root: Repository root directory
            number: Issue number to close

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    @abstractmethod
    def get_current_username(self) -> str | None:
        """Get the current authenticated GitHub username.

        Returns:
            GitHub username if authenticated, None if not authenticated

        Note:
            This is a global operation (not repository-specific).
            Used for attribution in plan creation (created_by field).
        """
        ...

    @abstractmethod
    def get_prs_referencing_issue(
        self,
        repo_root: Path,
        issue_number: int,
    ) -> list[PRReference]:
        """Get PRs that reference an issue via REST timeline API.

        Returns lightweight PR info (number, state, is_draft) for PRs
        that cross-reference this issue. Does not filter by willCloseTarget.

        For erk-plan issues, any referencing PR is considered linked.

        Args:
            repo_root: Path to repository root
            issue_number: Issue number to find referencing PRs for

        Returns:
            List of PRReference objects for PRs that reference the issue
        """
        ...

    @abstractmethod
    def add_reaction_to_comment(
        self,
        repo_root: Path,
        comment_id: int,
        reaction: str,
    ) -> None:
        """Add a reaction to an issue/PR comment.

        Used to mark PR discussion comments as addressed (typically with +1).

        Args:
            repo_root: Repository root path
            comment_id: Numeric comment ID (from IssueComment.id)
            reaction: Reaction type. One of: +1, -1, laugh, confused,
                heart, hooray, rocket, eyes

        Raises:
            RuntimeError: If gh CLI fails (not installed, not authenticated,
                comment not found, or invalid reaction)
        """
        ...

    @abstractmethod
    def update_comment(
        self,
        repo_root: Path,
        comment_id: int,
        body: str,
    ) -> None:
        """Update the body of an existing issue comment.

        Args:
            repo_root: Repository root path
            comment_id: Numeric comment ID (from IssueComment.id)
            body: New comment body markdown

        Raises:
            RuntimeError: If gh CLI fails (not installed, not authenticated,
                or comment not found)
        """
        ...
