"""GitHub implementation of plan storage.

Schema Version 2:
- Issue body contains only compact metadata (for fast querying)
- First comment contains the plan content (wrapped in markers)
- Plan content is always fetched fresh (no caching)
"""

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from erk_shared.github.issues import GitHubIssues, IssueInfo
from erk_shared.github.metadata import (
    extract_plan_from_comment,
    format_plan_content_comment,
    format_plan_header_body,
    update_plan_header_dispatch,
    update_plan_header_local_impl,
    update_plan_header_remote_impl,
    update_plan_header_worktree_name,
)
from erk_shared.plan_store.store import PlanStore
from erk_shared.plan_store.types import (
    CreatePlanResult,
    Plan,
    PlanMetadataUpdate,
    PlanQuery,
    PlanState,
)


class GitHubPlanStore(PlanStore):
    """GitHub implementation using gh CLI.

    Wraps GitHub issue operations and converts to provider-agnostic Plan format.

    Schema Version 2 Support:
    - For new-format issues: body contains metadata, first comment contains plan
    - For old-format issues: body contains plan content directly (backward compatible)
    """

    def __init__(self, github_issues: GitHubIssues):
        """Initialize GitHubPlanStore with GitHub issues interface.

        Args:
            github_issues: GitHubIssues implementation to use for issue operations
        """
        self._github_issues = github_issues

    def get_plan(self, repo_root: Path, plan_identifier: str) -> Plan:
        """Fetch plan from GitHub by identifier.

        Schema Version 2:
        1. Fetch issue (body contains metadata)
        2. Fetch first comment (contains plan content) - always fresh
        3. Extract plan from comment using extract_plan_from_comment()
        4. Return Plan with extracted plan content as body

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

        # Fetch first comment (always fresh - no caching)
        comments = self._github_issues.get_issue_comments(repo_root, issue_number)

        # Try to extract plan content from first comment (schema version 2)
        plan_body = None
        if comments:
            first_comment = comments[0]
            plan_body = extract_plan_from_comment(first_comment)

        # Fallback to issue body for backward compatibility (old format)
        if plan_body is None:
            plan_body = issue_info.body

        # Validate plan has meaningful content
        if not plan_body or not plan_body.strip():
            msg = (
                f"Plan content is empty for issue {plan_identifier}. "
                "Ensure the issue body or first comment contains plan content."
            )
            raise RuntimeError(msg)

        return self._convert_to_plan(issue_info, plan_body)

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
            plan_body: Plan content (extracted from comment for schema v2, or from body for v1)
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

    # === WRITE OPERATIONS ===

    def create_plan(
        self,
        repo_root: Path,
        title: str,
        body: str,
        labels: list[str],
    ) -> CreatePlanResult:
        """Create GitHub issue with plan content.

        Schema V2: Metadata in issue body, plan content in first comment.

        Args:
            repo_root: Repository root directory
            title: Plan title (without [erk-plan] suffix - added automatically)
            body: Plan content (markdown)
            labels: Additional labels (erk-plan added automatically)

        Returns:
            CreatePlanResult with plan_identifier and url

        Raises:
            RuntimeError: If gh CLI fails
        """
        timestamp = datetime.now(UTC).isoformat()
        creator = self._github_issues.get_current_username() or "unknown"

        # Format issue body (metadata only for Schema V2)
        issue_body = format_plan_header_body(
            created_at=timestamp,
            created_by=creator,
        )

        # Create issue with [erk-plan] suffix
        issue_title = f"{title} [erk-plan]"
        all_labels = ["erk-plan"] + [label for label in labels if label != "erk-plan"]

        result = self._github_issues.create_issue(
            repo_root=repo_root,
            title=issue_title,
            body=issue_body,
            labels=all_labels,
        )

        # Add plan content as first comment (Schema V2)
        comment_body = format_plan_content_comment(body)
        self._github_issues.add_comment(repo_root, result.number, comment_body)

        return CreatePlanResult(
            plan_identifier=str(result.number),
            url=result.url,
        )

    def update_plan_metadata(
        self,
        repo_root: Path,
        plan_identifier: str,
        updates: PlanMetadataUpdate,
    ) -> None:
        """Update plan-header block in issue body.

        Applies provided metadata updates to the existing plan-header block.
        Each non-None field in updates will be written to the plan header.

        Args:
            repo_root: Repository root directory
            plan_identifier: Issue number as string
            updates: Metadata fields to update

        Raises:
            RuntimeError: If gh CLI fails or plan not found
        """
        issue_number = int(plan_identifier)
        issue = self._github_issues.get_issue(repo_root, issue_number)
        updated_body = issue.body

        # Apply each update in sequence (order doesn't matter since each
        # update reads the latest block state before modifying)
        if updates.worktree_name is not None:
            updated_body = update_plan_header_worktree_name(updated_body, updates.worktree_name)

        if updates.last_dispatched_run_id is not None and updates.last_dispatched_at is not None:
            updated_body = update_plan_header_dispatch(
                updated_body, updates.last_dispatched_run_id, updates.last_dispatched_at
            )

        if updates.last_local_impl_at is not None:
            updated_body = update_plan_header_local_impl(updated_body, updates.last_local_impl_at)

        if updates.last_remote_impl_at is not None:
            updated_body = update_plan_header_remote_impl(updated_body, updates.last_remote_impl_at)

        # Only update if body actually changed
        if updated_body != issue.body:
            self._github_issues.update_issue_body(repo_root, issue_number, updated_body)

    def ensure_label(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Ensure label exists in repository.

        Creates the label if it doesn't exist, no-op if it does.

        Args:
            repo_root: Repository root directory
            label: Label name
            description: Label description
            color: Label color (6-char hex, no #)

        Raises:
            RuntimeError: If gh CLI fails
        """
        self._github_issues.ensure_label_exists(repo_root, label, description, color)

    def get_current_user(self) -> str | None:
        """Get current authenticated GitHub user.

        Returns:
            Username or None if not authenticated
        """
        return self._github_issues.get_current_username()
