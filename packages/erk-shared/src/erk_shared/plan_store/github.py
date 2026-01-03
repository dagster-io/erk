"""GitHub implementation of plan storage.

Schema Version 2:
- Issue body contains only compact metadata (for fast querying)
- First comment contains the plan content (wrapped in markers)
- Plan content is always fetched fresh (no caching)
"""

import sys
from datetime import UTC
from pathlib import Path
from urllib.parse import urlparse

from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime
from erk_shared.github.issues import GitHubIssues, IssueInfo
from erk_shared.github.metadata import extract_plan_from_comment, extract_plan_header_comment_id
from erk_shared.github.retry import RetriesExhausted, RetryRequested, with_retries
from erk_shared.plan_store.store import PlanStore
from erk_shared.plan_store.types import Plan, PlanQuery, PlanState


class GitHubPlanStore(PlanStore):
    """GitHub implementation using gh CLI.

    Wraps GitHub issue operations and converts to provider-agnostic Plan format.

    Schema Version 2 Support:
    - For new-format issues: body contains metadata, first comment contains plan
    - For old-format issues: body contains plan content directly (backward compatible)
    """

    def __init__(self, github_issues: GitHubIssues, time: Time | None = None):
        """Initialize GitHubPlanStore with GitHub issues interface and optional time dependency.

        Args:
            github_issues: GitHubIssues implementation to use for issue operations
            time: Time abstraction for sleep operations. Defaults to RealTime() for
                  production use. Pass FakeTime() in tests that need to verify retry behavior.
        """
        self._github_issues = github_issues
        self._time = time if time is not None else RealTime()

    def get_plan(self, repo_root: Path, plan_identifier: str) -> Plan:
        """Fetch plan from GitHub by identifier.

        Schema Version 2:
        1. Fetch issue (body contains metadata)
        2. Check for plan_comment_id in metadata for direct lookup
        3. If plan_comment_id exists, fetch that specific comment
        4. Otherwise, fall back to fetching first comment
        5. Extract plan from comment using extract_plan_from_comment()
        6. Return Plan with extracted plan content as body

        Backward Compatibility:
        - If no first comment with plan markers found, falls back to issue body
        - This supports old-format issues where plan was in the body directly

        Args:
            repo_root: Repository root directory
            plan_identifier: Issue number as string (e.g., "42")

        Returns:
            Plan with converted data (plan content in body field)

        Raises:
            RuntimeError: If gh CLI fails or plan not found
        """
        issue_number = int(plan_identifier)
        issue_info = self._github_issues.get_issue(repo_root, issue_number)
        plan_body = self._get_plan_body(repo_root, issue_info)
        return self._convert_to_plan(issue_info, plan_body)

    def _fetch_comment_with_retry(
        self,
        repo_root: Path,
        comment_id: int,
    ) -> str | None:
        """Fetch comment by ID with retry logic for transient errors.

        Attempts to fetch the comment with exponential backoff to handle
        transient GitHub API failures. Falls back gracefully if the comment
        is permanently missing (deleted, invalid ID).

        Uses with_github_retry utility which retries up to 2 times
        (3 total attempts) with delays of 0.5s and 1s.

        Args:
            repo_root: Repository root directory
            comment_id: GitHub comment ID to fetch

        Returns:
            Plan content extracted from comment, or None if fetch fails
        """

        def fetch_comment() -> str | RetryRequested:
            try:
                return self._github_issues.get_comment_by_id(repo_root, comment_id)
            except RuntimeError as e:
                return RetryRequested(reason=f"API error: {e}")

        result = with_retries(
            self._time,
            f"fetch plan comment {comment_id}",
            fetch_comment,
        )
        if isinstance(result, RetriesExhausted):
            # All retries exhausted - fall back to first comment
            print(
                "Falling back to first comment lookup (comment may be deleted)",
                file=sys.stderr,
            )
            return None
        # with_retries never returns RetryRequested - it converts to RetriesExhausted
        assert isinstance(result, str)
        return extract_plan_from_comment(result)

    def _get_plan_body(self, repo_root: Path, issue_info: IssueInfo) -> str:
        """Get the plan body from the issue.

        Args:
            repo_root: Repository root directory
            issue_info: IssueInfo from GitHubIssues interface

        Returns:
            Plan body as string
        """
        plan_body = None
        plan_comment_id = extract_plan_header_comment_id(issue_info.body)
        if plan_comment_id is not None:
            plan_body = self._fetch_comment_with_retry(repo_root, plan_comment_id)

        if plan_body:
            return plan_body

        comments = self._github_issues.get_issue_comments(repo_root, issue_info.number)
        if comments:
            first_comment = comments[0]
            plan_body = extract_plan_from_comment(first_comment)

        if plan_body:
            return plan_body

        plan_body = issue_info.body

        # Validate plan has meaningful content
        if not plan_body or not plan_body.strip():
            msg = (
                f"Plan content is empty for issue {issue_info.number}. "
                "Ensure the issue body or first comment contains plan content."
            )
            raise RuntimeError(msg)

        return plan_body

    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        """Query plans from GitHub.

        Args:
            repo_root: Repository root directory
            query: Filter criteria (labels, state, limit)

        Returns:
            List of Plan matching the criteria

        Raises:
            RuntimeError: If gh CLI fails
        """
        # Map PlanState to GitHub state string
        state_str = None
        if query.state == PlanState.OPEN:
            state_str = "open"
        elif query.state == PlanState.CLOSED:
            state_str = "closed"

        # Use GitHubIssues native limit support for efficient querying
        issues = self._github_issues.list_issues(
            repo_root,
            labels=query.labels,
            state=state_str,
            limit=query.limit,
        )

        return [self._convert_to_plan(issue) for issue in issues]

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "github"
        """
        return "github"

    def close_plan(self, repo_root: Path, identifier: str) -> None:
        """Close a plan by its identifier.

        Args:
            repo_root: Repository root directory
            identifier: Plan identifier (issue number like "123" or GitHub URL)

        Raises:
            RuntimeError: If gh CLI fails, plan not found, or invalid identifier
        """
        # Parse identifier to extract issue number
        number = self._parse_identifier(identifier)

        # Add comment before closing
        comment_body = "Plan completed via erk plan close"
        self._github_issues.add_comment(repo_root, number, comment_body)

        # Close the issue
        self._github_issues.close_issue(repo_root, number)

    def _parse_identifier(self, identifier: str) -> int:
        """Parse identifier to extract issue number.

        Args:
            identifier: Issue number (e.g., "123") or GitHub URL

        Returns:
            Issue number as integer

        Raises:
            RuntimeError: If identifier format is invalid
        """
        # Check if it's a simple numeric string
        if identifier.isdigit():
            return int(identifier)

        # Check if it's a GitHub URL
        # Security: Use proper URL parsing to validate hostname
        parsed = urlparse(identifier)
        if parsed.hostname == "github.com" and parsed.path:
            # Extract number from URL: https://github.com/org/repo/issues/123
            parts = parsed.path.rstrip("/").split("/")
            if len(parts) >= 2 and parts[-2] == "issues":
                issue_num_str = parts[-1]
                if issue_num_str.isdigit():
                    return int(issue_num_str)

        # Invalid identifier format
        msg = (
            f"Invalid identifier format: {identifier}. "
            "Expected issue number (e.g., '123') or GitHub URL"
        )
        raise RuntimeError(msg)

    def _convert_to_plan(self, issue_info: IssueInfo, plan_body: str | None = None) -> Plan:
        """Convert IssueInfo to Plan.

        Args:
            issue_info: IssueInfo from GitHubIssues interface
            plan_body: Plan content extracted from comment, or issue body as fallback.
                       If None, uses issue_info.body (for list_plans compatibility)

        Returns:
            Plan with normalized data
        """
        # Normalize state
        state = PlanState.OPEN if issue_info.state == "OPEN" else PlanState.CLOSED

        # Store GitHub-specific number in metadata for future operations
        metadata: dict[str, object] = {"number": issue_info.number}

        # Use provided plan_body or fall back to issue body
        body = plan_body if plan_body is not None else issue_info.body

        return Plan(
            plan_identifier=str(issue_info.number),
            title=issue_info.title,
            body=body,
            state=state,
            url=issue_info.url,
            labels=issue_info.labels,
            assignees=issue_info.assignees,
            created_at=issue_info.created_at.astimezone(UTC),
            updated_at=issue_info.updated_at.astimezone(UTC),
            metadata=metadata,
        )
