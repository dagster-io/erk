"""Abstract base class for GitHub issue operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.github.issue.types import (
    CreateIssueResult,
    DevelopmentBranch,
    IssueComment,
    IssueInfo,
)


class GitHubIssueGateway(ABC):
    """Abstract interface for GitHub issue operations.

    Consolidates GitHubIssues + IssueLinkBranches interfaces.
    All implementations (real and fake) must implement this interface.
    """

    # --- Issue CRUD operations ---

    @abstractmethod
    def create_issue(
        self, repo_root: Path, title: str, body: str, labels: list[str]
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
    def list_issues(
        self,
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
    def close_issue(self, repo_root: Path, number: int) -> None:
        """Close a GitHub issue.

        Args:
            repo_root: Repository root directory
            number: Issue number to close

        Raises:
            RuntimeError: If gh CLI fails or issue not found
        """
        ...

    # --- Issue body operations ---

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

    # --- Comment operations ---

    @abstractmethod
    def add_comment(self, repo_root: Path, number: int, body: str) -> None:
        """Add a comment to an existing issue.

        Args:
            repo_root: Repository root directory
            number: Issue number to comment on
            body: Comment body markdown

        Raises:
            RuntimeError: If gh CLI fails or issue not found
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
    def get_multiple_issue_comments(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[str]]:
        """Fetch comments for multiple issues in a single batch operation.

        Uses GitHub GraphQL API to fetch all issue comments in one request,
        significantly reducing API calls and improving performance.

        Args:
            repo_root: Path to repository root
            issue_numbers: List of issue numbers to fetch comments for

        Returns:
            Mapping of issue number to list of comment bodies (markdown strings).
            Issues without comments will have an empty list.

        Raises:
            RuntimeError: If gh CLI fails
        """
        ...

    # --- Label operations ---

    @abstractmethod
    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
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

    # --- Development branch operations (from IssueLinkBranches) ---

    @abstractmethod
    def create_development_branch(
        self,
        repo_root: Path,
        issue_number: int,
        *,
        branch_name: str,
        base_branch: str | None = None,
    ) -> DevelopmentBranch:
        """Create a development branch linked to an issue via gh issue develop.

        If a development branch already exists for the issue, returns that
        branch name with already_existed=True.

        Args:
            repo_root: Repository root directory
            issue_number: GitHub issue number to link the branch to
            branch_name: The branch name to use. Passed to gh issue develop --name
                        to ensure branch names match worktree naming conventions.
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
