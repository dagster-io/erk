"""Thin wrapper around Erk context for slackbot operations."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.github.issues.types import CreateIssueResult, IssueInfo
from erk_shared.github.metadata import format_plan_content_comment, format_plan_header_body
from erk_shared.plan_utils import extract_title_from_plan

from erk.cli.constants import DISPATCH_WORKFLOW_NAME, ERK_PLAN_LABEL
from erk.core.context import ErkContext, create_context


@dataclass(frozen=True)
class CreatePlanResult:
    """Result from creating a plan."""

    issue_number: int
    url: str
    title: str


@dataclass(frozen=True)
class SubmitResult:
    """Result from submitting a plan to the queue."""

    run_id: str
    workflow_url: str


@dataclass(frozen=True)
class PlanInfo:
    """Information about a plan issue."""

    number: int
    title: str
    state: str
    url: str
    created_at: datetime


class ErkService:
    """Thin wrapper around Erk's context that provides three operations.

    This service abstracts Erk's core functionality for use by the Slack bot:
    - Creating plans from markdown content
    - Submitting plans to the Erk queue
    - Listing open plans

    Attributes:
        repo_path: Path to the git repository
    """

    def __init__(self, repo_path: Path) -> None:
        """Initialize the ErkService.

        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path
        self._ctx: ErkContext | None = None

    @property
    def ctx(self) -> ErkContext:
        """Get or create the ErkContext lazily."""
        if self._ctx is None:
            self._ctx = create_context(dry_run=False)
        return self._ctx

    def create_plan(self, content: str, title: str | None = None) -> CreatePlanResult:
        """Create a plan issue from markdown content.

        Args:
            content: Plan markdown content
            title: Optional custom title (extracts from H1 if not provided)

        Returns:
            CreatePlanResult with issue number, URL, and title

        Raises:
            ValueError: If content is empty
            RuntimeError: If GitHub operations fail
        """
        content = content.strip()
        if not content:
            raise ValueError("Plan content is empty")

        # Extract or use provided title
        if title is None:
            title = extract_title_from_plan(content)

        if not title.strip():
            raise ValueError("Could not extract title from plan")

        # Ensure erk-plan label exists
        self.ctx.issues.ensure_label_exists(
            self.repo_path,
            label=ERK_PLAN_LABEL,
            description="Implementation plan tracked by erk",
            color="0E8A16",
        )

        # Create timestamp and get creator
        timestamp = datetime.now(UTC).isoformat()
        creator = self.ctx.issues.get_current_username() or "slackbot"

        # Format issue body (Schema V2: metadata only)
        issue_body = format_plan_header_body(
            created_at=timestamp,
            created_by=creator,
        )

        # Create the issue with [erk-plan] suffix
        issue_title = f"{title} [erk-plan]"
        result: CreateIssueResult = self.ctx.issues.create_issue(
            repo_root=self.repo_path,
            title=issue_title,
            body=issue_body,
            labels=[ERK_PLAN_LABEL],
        )

        # Add plan content as first comment (Schema V2 format)
        comment_body = format_plan_content_comment(content)
        self.ctx.issues.add_comment(self.repo_path, result.number, comment_body)

        return CreatePlanResult(
            issue_number=result.number,
            url=result.url,
            title=title,
        )

    def submit_to_queue(self, issue_number: int, submitted_by: str) -> SubmitResult:
        """Submit a plan to the Erk queue for remote implementation.

        Args:
            issue_number: GitHub issue number
            submitted_by: Username of the person submitting

        Returns:
            SubmitResult with run_id and workflow_url

        Raises:
            ValueError: If issue is not a valid erk-plan or is closed
            RuntimeError: If GitHub operations fail
        """
        # Fetch and validate issue
        issue: IssueInfo = self.ctx.issues.get_issue(self.repo_path, issue_number)

        if ERK_PLAN_LABEL not in issue.labels:
            raise ValueError(f"Issue #{issue_number} does not have {ERK_PLAN_LABEL} label")

        if issue.state != "OPEN":
            raise ValueError(f"Issue #{issue_number} is {issue.state}, not OPEN")

        # Trigger workflow
        run_id = self.ctx.github.trigger_workflow(
            repo_root=self.repo_path,
            workflow=DISPATCH_WORKFLOW_NAME,
            inputs={
                "issue_number": str(issue_number),
                "submitted_by": submitted_by,
                "issue_title": issue.title,
            },
        )

        # Construct workflow URL from issue URL
        workflow_url = self._construct_workflow_url(issue.url, run_id)

        return SubmitResult(run_id=run_id, workflow_url=workflow_url)

    def list_plans(self, limit: int = 20) -> list[PlanInfo]:
        """List open erk-plan issues.

        Args:
            limit: Maximum number of plans to return (default 20)

        Returns:
            List of PlanInfo sorted by creation date (newest first)
        """
        issues: list[IssueInfo] = self.ctx.issues.list_issues(
            self.repo_path,
            labels=[ERK_PLAN_LABEL],
            state="open",
            limit=limit,
        )

        return [
            PlanInfo(
                number=issue.number,
                title=issue.title,
                state=issue.state,
                url=issue.url,
                created_at=issue.created_at,
            )
            for issue in issues
        ]

    def _construct_workflow_url(self, issue_url: str, run_id: str) -> str:
        """Construct GitHub Actions workflow run URL from issue URL and run ID."""
        parts = issue_url.split("/")
        if len(parts) >= 5:
            owner = parts[-4]
            repo = parts[-3]
            return f"https://github.com/{owner}/{repo}/actions/runs/{run_id}"
        return f"https://github.com/actions/runs/{run_id}"
