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
from erk_shared.github.metadata.plan_header import (
    extract_plan_from_comment,
    extract_plan_header_comment_id,
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
            repo_root=repo_root,
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

    def create_plan(
        self,
        *,
        repo_root: Path,
        title: str,
        content: str,
        labels: tuple[str, ...],
        metadata: Mapping[str, object],
    ) -> CreatePlanResult:
        """Create a new plan issue.

        Delegates to create_plan_issue() which handles:
        - GitHub authentication validation
        - Label creation
        - Issue creation with metadata body
        - Plan content comment creation

        Args:
            repo_root: Repository root directory
            title: Plan title
            content: Plan body/description
            labels: Labels to apply (immutable tuple)
            metadata: Provider-specific metadata. Supported keys:
                - plan_type: str | None (e.g., "extraction")
                - title_suffix: str | None
                - source_plan_issues: list[int] | None
                - extraction_session_ids: list[str] | None
                - source_repo: str | None
                - objective_issue: int | None

        Returns:
            CreatePlanResult with plan_id and url

        Raises:
            RuntimeError: If plan creation fails completely (no partial success)
        """
        # Extract and convert metadata fields with explicit type handling
        plan_type_raw = metadata.get("plan_type")
        plan_type_str: str | None = str(plan_type_raw) if plan_type_raw is not None else None

        title_suffix_raw = metadata.get("title_suffix")
        title_suffix_str: str | None = None
        if title_suffix_raw is not None:
            title_suffix_str = str(title_suffix_raw)

        source_repo_raw = metadata.get("source_repo")
        source_repo_str: str | None = str(source_repo_raw) if source_repo_raw is not None else None

        # Handle list fields - must be iterables
        source_plan_issues_raw = metadata.get("source_plan_issues")
        source_plan_issues_list: list[int] | None = None
        if source_plan_issues_raw is not None and hasattr(source_plan_issues_raw, "__iter__"):
            source_plan_issues_list = [int(x) for x in source_plan_issues_raw]  # type: ignore[union-attr]

        extraction_session_ids_raw = metadata.get("extraction_session_ids")
        extraction_session_ids_list: list[str] | None = None
        if extraction_session_ids_raw is not None:
            if hasattr(extraction_session_ids_raw, "__iter__"):
                ids_raw: list[object] = list(extraction_session_ids_raw)  # type: ignore[arg-type]
                extraction_session_ids_list = [str(x) for x in ids_raw]

        # Handle int field
        objective_issue_raw = metadata.get("objective_issue")
        objective_issue_int: int | None = None
        if objective_issue_raw is not None:
            objective_issue_int = int(objective_issue_raw)  # type: ignore[arg-type]

        # Convert tuple labels to list, excluding standard 'erk-plan' label
        # since create_plan_issue adds it automatically
        extra_labels = [lbl for lbl in labels if lbl != "erk-plan"]

        # Extract created_from_session from metadata if provided
        created_from_session_raw = metadata.get("created_from_session")
        created_from_session_str: str | None = (
            str(created_from_session_raw) if created_from_session_raw is not None else None
        )

        result = create_plan_issue(
            github_issues=self._github_issues,
            repo_root=repo_root,
            plan_content=content,
            title=title,
            plan_type=plan_type_str,
            extra_labels=extra_labels if extra_labels else None,
            title_suffix=title_suffix_str,
            source_plan_issues=source_plan_issues_list,
            extraction_session_ids=extraction_session_ids_list,
            source_repo=source_repo_str,
            objective_issue=objective_issue_int,
            created_from_session=created_from_session_str,
        )

        if not result.success:
            # For full failures (no issue created), raise RuntimeError
            if result.issue_number is None:
                error_msg = result.error or "Unknown error creating plan"
                raise RuntimeError(error_msg)

            # For partial success (issue created but comment failed),
            # still return success since the plan was created
            # The caller can check the error field if needed

        # At this point result is either full success or partial success with issue_number set
        issue_number = result.issue_number
        if issue_number is None:
            raise RuntimeError("Unexpected: issue_number is None after successful creation")

        return CreatePlanResult(
            plan_id=str(issue_number),
            url=result.issue_url or "",
        )

    def update_metadata(
        self,
        repo_root: Path,
        plan_id: str,
        metadata: Mapping[str, object],
    ) -> None:
        """Update plan metadata in the issue body.

        Fetches the current issue body, updates the plan-header metadata block
        with allowed fields, and updates the issue body.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier (issue number)
            metadata: New metadata to set. Allowed fields:
                - worktree_name
                - last_dispatched_run_id
                - last_dispatched_node_id
                - last_dispatched_at
                - last_local_impl_at
                - last_local_impl_event
                - last_local_impl_session
                - last_local_impl_user
                - last_remote_impl_at

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        # Import here to avoid circular imports
        from erk_shared.github.metadata.core import (
            find_metadata_block,
            render_metadata_block,
            replace_metadata_block_in_body,
        )
        from erk_shared.github.metadata.schemas import PlanHeaderSchema
        from erk_shared.github.metadata.types import MetadataBlock

        issue_number = int(plan_id)
        issue_info = self._github_issues.get_issue(repo_root, issue_number)

        # Parse current metadata from issue body
        block = find_metadata_block(issue_info.body, "plan-header")
        if block is None:
            raise RuntimeError("plan-header block not found in issue body")

        current_data = dict(block.data)

        # Whitelist of allowed metadata fields
        allowed_fields = {
            "worktree_name",
            "last_dispatched_run_id",
            "last_dispatched_node_id",
            "last_dispatched_at",
            "last_local_impl_at",
            "last_local_impl_event",
            "last_local_impl_session",
            "last_local_impl_user",
            "last_remote_impl_at",
        }

        # Merge allowed fields from new metadata
        for key, value in metadata.items():
            if key in allowed_fields:
                current_data[key] = value

        # Validate updated data
        schema = PlanHeaderSchema()
        schema.validate(current_data)

        # Create new block and render
        new_block = MetadataBlock(key="plan-header", data=current_data)
        new_block_content = render_metadata_block(new_block)

        # Replace block in full body and update issue
        updated_body = replace_metadata_block_in_body(
            issue_info.body, "plan-header", new_block_content
        )
        self._github_issues.update_issue_body(repo_root, issue_number, updated_body)

    def add_comment(
        self,
        repo_root: Path,
        plan_id: str,
        body: str,
    ) -> str:
        """Add a comment to a plan.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier (issue number)
            body: Comment body text

        Returns:
            Comment ID as string

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        issue_number = int(plan_id)
        comment_id = self._github_issues.add_comment(repo_root, issue_number, body)
        return str(comment_id)

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
