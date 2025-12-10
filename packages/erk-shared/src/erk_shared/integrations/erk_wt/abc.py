"""Abstract operations interface for erk worktree creation from issues.

This module defines ABC interfaces for operations needed by create_wt_from_issue command.
These interfaces enable dependency injection with in-memory fakes for testing while
maintaining type safety.

Design:
- Single ErkWtKit interface combining all necessary operations
- Return values use LBYL pattern (None/False on failure, not exceptions)
- Data classes for structured return values
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class IssueParseResult:
    """Result of parsing an issue reference (number or URL).

    Attributes:
        success: Whether parsing succeeded
        issue_number: Parsed issue number (only if success=True)
        error: Error type code (only if success=False)
        message: Human-readable message (present for both success and failure)
    """

    success: bool
    issue_number: int | None = None
    error: str | None = None
    message: str | None = None


@dataclass
class IssueData:
    """GitHub issue data returned from gh CLI.

    Attributes:
        number: Issue number
        title: Issue title
        body: Issue body (markdown content)
        state: Issue state (open, closed, etc.)
        url: Full URL to the issue
        labels: List of label names
    """

    number: int
    title: str
    body: str
    state: str
    url: str
    labels: list[str]


@dataclass
class WorktreeCreationResult:
    """Result of creating a worktree via erk create command.

    Attributes:
        success: Whether worktree creation succeeded
        worktree_name: Name of created worktree (only if success=True)
        worktree_path: Absolute path to worktree (only if success=True)
        branch_name: Git branch name (only if success=True)
    """

    success: bool
    worktree_name: str | None = None
    worktree_path: str | None = None
    branch_name: str | None = None


class ErkWtKit(ABC):
    """Operations interface for erk worktree creation from issues.

    This interface wraps all subprocess calls needed by create_wt_from_issue command:
    - erk kit exec erk parse-issue-reference
    - gh issue view
    - erk create --from-plan
    - erk kit exec erk comment-worktree-creation
    - gh issue edit
    """

    @abstractmethod
    def parse_issue_reference(self, issue_arg: str) -> IssueParseResult:
        """Parse issue reference (number or URL) into issue number.

        Args:
            issue_arg: Issue number (e.g., "123") or GitHub URL

        Returns:
            IssueParseResult with success status and issue number or error
        """

    @abstractmethod
    def fetch_issue(self, issue_number: int) -> IssueData | None:
        """Fetch issue data from GitHub via gh CLI.

        Args:
            issue_number: GitHub issue number

        Returns:
            IssueData if fetch succeeded, None otherwise
        """

    @abstractmethod
    def create_worktree(self, plan_content: str) -> WorktreeCreationResult:
        """Create worktree from plan content using erk create command.

        Args:
            plan_content: Plan markdown content

        Returns:
            WorktreeCreationResult with success status and worktree details
        """

    @abstractmethod
    def post_creation_comment(
        self, issue_number: int, worktree_name: str, branch_name: str
    ) -> bool:
        """Post worktree creation comment to GitHub issue.

        Args:
            issue_number: GitHub issue number
            worktree_name: Name of created worktree
            branch_name: Git branch name

        Returns:
            True if comment posted successfully, False otherwise
        """

    @abstractmethod
    def update_issue_body(self, issue_number: int, body: str) -> bool:
        """Update issue body via gh issue edit.

        Args:
            issue_number: GitHub issue number
            body: New issue body content

        Returns:
            True if update succeeded, False otherwise
        """
