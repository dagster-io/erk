"""In-memory fake implementation of erk worktree operations for testing.

This module provides a fake implementation that eliminates the need for subprocess
mocking in tests. Uses constructor injection for declarative test setup.

Design:
- Constructor injection for all test data (issues, parse results, worktree results)
- Mutation tracking for assertions (read-only lists of operations performed)
- No I/O operations (everything in-memory)
- Returns match interface contracts exactly
- Follows fake-driven-testing patterns
"""

from erk_shared.gateway.erk_wt.abc import (
    ErkWtKit,
    IssueData,
    IssueParseResult,
    WorktreeCreationResult,
)


class FakeErkWtKit(ErkWtKit):
    """Fake erk worktree operations with in-memory state."""

    def __init__(
        self,
        *,
        issues: dict[int, IssueData] | None = None,
        parse_results: dict[str, IssueParseResult] | None = None,
        worktree_result: WorktreeCreationResult | None = None,
        comment_success: bool = True,
        update_body_success: bool = True,
    ) -> None:
        """Initialize fake with test data.

        Args:
            issues: Map of issue_number -> IssueData for fetch_issue
            parse_results: Map of issue_arg -> IssueParseResult for parse_issue_reference
            worktree_result: Result to return from create_worktree
            comment_success: Whether post_creation_comment should succeed
            update_body_success: Whether update_issue_body should succeed
        """
        self._issues = issues if issues is not None else {}
        self._parse_results = parse_results if parse_results is not None else {}
        self._worktree_result = (
            worktree_result
            if worktree_result is not None
            else WorktreeCreationResult(success=False)
        )
        self._comment_success = comment_success
        self._update_body_success = update_body_success

        # Mutation tracking (read-only properties for assertions)
        self._created_worktrees: list[str] = []
        self._posted_comments: list[tuple[int, str, str]] = []
        self._updated_bodies: list[tuple[int, str]] = []

    # Read-only properties for mutation tracking

    @property
    def created_worktrees(self) -> list[str]:
        """List of plan contents passed to create_worktree (read-only)."""
        return self._created_worktrees

    @property
    def posted_comments(self) -> list[tuple[int, str, str]]:
        """List of (issue_number, worktree_name, branch_name) for posted comments (read-only)."""
        return self._posted_comments

    @property
    def updated_bodies(self) -> list[tuple[int, str]]:
        """List of (issue_number, body) for updated issue bodies (read-only)."""
        return self._updated_bodies

    # Interface implementation

    def parse_issue_reference(self, issue_arg: str) -> IssueParseResult:
        """Parse issue reference using pre-configured results.

        Args:
            issue_arg: Issue number or GitHub URL

        Returns:
            IssueParseResult from parse_results dict, or error if not found
        """
        if issue_arg in self._parse_results:
            return self._parse_results[issue_arg]

        # Default: return failure
        return IssueParseResult(
            success=False,
            error="not_configured",
            message=f"No parse result configured for '{issue_arg}'",
        )

    def fetch_issue(self, issue_number: int) -> IssueData | None:
        """Fetch issue data from pre-configured issues dict.

        Args:
            issue_number: GitHub issue number

        Returns:
            IssueData from issues dict, or None if not found
        """
        if issue_number not in self._issues:
            return None

        return self._issues[issue_number]

    def create_worktree(self, plan_content: str) -> WorktreeCreationResult:
        """Create worktree and track mutation.

        Args:
            plan_content: Plan markdown content

        Returns:
            Pre-configured WorktreeCreationResult
        """
        # Track mutation
        self._created_worktrees.append(plan_content)

        return self._worktree_result

    def post_creation_comment(
        self, issue_number: int, worktree_name: str, branch_name: str
    ) -> bool:
        """Post creation comment and track mutation.

        Args:
            issue_number: GitHub issue number
            worktree_name: Name of created worktree
            branch_name: Git branch name

        Returns:
            Pre-configured success value
        """
        # Track mutation
        self._posted_comments.append((issue_number, worktree_name, branch_name))

        return self._comment_success

    def update_issue_body(self, issue_number: int, body: str) -> bool:
        """Update issue body and track mutation.

        Args:
            issue_number: GitHub issue number
            body: New issue body content

        Returns:
            Pre-configured success value
        """
        # Track mutation
        self._updated_bodies.append((issue_number, body))

        return self._update_body_success
