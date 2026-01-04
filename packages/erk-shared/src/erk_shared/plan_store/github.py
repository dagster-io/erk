"""GitHub implementation of plan storage.

Schema Version 2:
- Issue body contains only compact metadata (for fast querying)
- First comment contains the plan content (wrapped in markers)
- Plan content is always fetched fresh (no caching)
"""

import sys
from collections.abc import Mapping
from datetime import UTC
from pathlib import Path
from urllib.parse import urlparse

from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime
from erk_shared.github.issues import GitHubIssues, IssueInfo
from erk_shared.github.metadata import (
    extract_plan_from_comment,
    extract_plan_header_comment_id,
    update_plan_header_metadata,
)
from erk_shared.github.plan_issues import create_plan_issue
from erk_shared.github.retry import RetriesExhausted, RetryRequested, with_retries
from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.types import CreatePlanResult, Plan, PlanQuery, PlanState


class GitHubPlanStore(PlanBackend):
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

    def get_plan(self, repo_root: Path, plan_id: str) -> Plan:
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
            plan_id: Issue number as string (e.g., "42")

        Returns:
            Plan with converted data (plan content in body field)

        Raises:
            RuntimeError: If gh CLI fails or plan not found
        """
        issue_number = int(plan_id)
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

    def close_plan(self, repo_root: Path, plan_id: str) -> None:
        """Close a plan by its identifier.

        Args:
            repo_root: Repository root directory
            plan_id: Plan identifier (issue number like "123" or GitHub URL)

        Raises:
            RuntimeError: If gh CLI fails, plan not found, or invalid identifier
        """
        # Parse identifier to extract issue number
        number = self._parse_identifier(plan_id)

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

    # Write operations (PlanBackend)

    def create_plan(
        self,
        repo_root: Path,
        title: str,
        content: str,
        labels: tuple[str, ...],
        metadata: Mapping[str, object],
    ) -> CreatePlanResult:
        """Create a new plan as a GitHub issue.

        Wraps create_plan_issue() to implement the PlanBackend interface.
        Uses Schema v2 format: metadata in issue body, plan content in first comment.

        Args:
            repo_root: Repository root directory
            title: Plan title (used as issue title)
            content: Plan body/description (plan content markdown)
            labels: Labels to apply (immutable tuple)
            metadata: Provider-specific metadata:
                - plan_type: Optional type discriminator ("extraction" or None)
                - objective_issue: Optional parent objective issue number
                - source_repo: Optional implementation repo in "owner/repo" format

        Returns:
            CreatePlanResult with plan_id and url

        Raises:
            RuntimeError: If GitHub API fails or issue creation fails
        """
        # Extract optional metadata fields
        plan_type = metadata.get("plan_type")
        if plan_type is not None and not isinstance(plan_type, str):
            msg = f"plan_type must be a string, got {type(plan_type).__name__}"
            raise RuntimeError(msg)

        objective_issue = metadata.get("objective_issue")
        if objective_issue is not None and not isinstance(objective_issue, int):
            msg = f"objective_issue must be an int, got {type(objective_issue).__name__}"
            raise RuntimeError(msg)

        source_repo = metadata.get("source_repo")
        if source_repo is not None and not isinstance(source_repo, str):
            msg = f"source_repo must be a string, got {type(source_repo).__name__}"
            raise RuntimeError(msg)

        # Convert extra_labels from labels tuple (exclude erk-plan which is auto-added)
        extra_labels = [label for label in labels if label != "erk-plan"]

        result = create_plan_issue(
            github_issues=self._github_issues,
            repo_root=repo_root,
            plan_content=content,
            title=title,
            plan_type=plan_type,
            extra_labels=extra_labels if extra_labels else None,
            title_suffix=None,  # Use default suffix based on plan_type
            source_plan_issues=None,  # Not exposed in PlanBackend interface
            extraction_session_ids=None,  # Not exposed in PlanBackend interface
            source_repo=source_repo,
            objective_issue=objective_issue,
        )

        if not result.success:
            msg = result.error or "Unknown error creating plan issue"
            raise RuntimeError(msg)

        # Result should have issue_number and issue_url if success is True
        if result.issue_number is None or result.issue_url is None:
            msg = "create_plan_issue returned success but missing issue_number or issue_url"
            raise RuntimeError(msg)

        return CreatePlanResult(
            plan_id=str(result.issue_number),
            url=result.issue_url,
        )

    def update_metadata(
        self,
        repo_root: Path,
        plan_id: str,
        metadata: Mapping[str, object],
    ) -> None:
        """Update plan metadata in the issue body.

        Updates the plan-header metadata block in the GitHub issue body.
        Only updates fields that are provided in the metadata mapping.

        Args:
            repo_root: Repository root directory
            plan_id: Issue number as string (e.g., "42")
            metadata: Fields to update in plan-header block. Supported fields:
                - worktree_name: str
                - last_local_impl_at: str (ISO timestamp)
                - last_local_impl_event: str ("started" or "ended")
                - last_local_impl_session: str (session ID)
                - last_local_impl_user: str (username)
                - last_remote_impl_at: str (ISO timestamp)
                - last_dispatched_run_id: str
                - last_dispatched_node_id: str
                - last_dispatched_at: str (ISO timestamp)
                - current_step: int

        Raises:
            RuntimeError: If GitHub API fails or issue not found
        """
        issue_number = int(plan_id)
        issue_info = self._github_issues.get_issue(repo_root, issue_number)

        # Update the plan-header metadata in issue body
        updated_body = update_plan_header_metadata(issue_info.body, metadata)

        # Write back to GitHub
        self._github_issues.update_issue_body(repo_root, issue_number, updated_body)

    def add_comment(
        self,
        repo_root: Path,
        plan_id: str,
        body: str,
    ) -> str:
        """Add a comment to a plan issue.

        Args:
            repo_root: Repository root directory
            plan_id: Issue number as string (e.g., "42")
            body: Comment body text (markdown)

        Returns:
            Comment ID as string

        Raises:
            RuntimeError: If GitHub API fails or issue not found
        """
        issue_number = int(plan_id)
        comment_id = self._github_issues.add_comment(repo_root, issue_number, body)
        return str(comment_id)
