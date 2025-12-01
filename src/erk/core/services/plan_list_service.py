"""Service for efficiently fetching plan list data via batched API calls.

Uses GraphQL nodes(ids: [...]) for O(1) batch lookup of workflow runs (~200ms for any N).
All plan issues store last_dispatched_node_id in the plan-header metadata block.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues, IssueInfo
from erk_shared.github.metadata import extract_plan_header_dispatch_info
from erk_shared.github.parsing import extract_owner_repo_from_github_url
from erk_shared.github.types import PullRequestInfo, WorkflowRun


@dataclass(frozen=True)
class PlanListData:
    """Combined data for plan listing (schema v2 only).

    Attributes:
        issues: List of IssueInfo objects
        pr_linkages: Mapping of issue_number -> list of PRs that close that issue
        workflow_runs: Mapping of issue_number -> most relevant WorkflowRun
    """

    issues: list[IssueInfo]
    pr_linkages: dict[int, list[PullRequestInfo]]
    workflow_runs: dict[int, WorkflowRun | None]


class PlanListService:
    """Service for efficiently fetching plan list data.

    Composes GitHub and GitHubIssues integrations to batch fetch all data
    needed for plan listing. Uses GraphQL nodes(ids: [...]) for efficient
    batch lookup of workflow runs by node_id.
    """

    def __init__(self, github: GitHub, github_issues: GitHubIssues) -> None:
        """Initialize PlanListService with required integrations.

        Args:
            github: GitHub integration for PR and workflow operations
            github_issues: GitHub issues integration for issue operations
        """
        self._github = github
        self._github_issues = github_issues

    def get_plan_list_data(
        self,
        repo_root: Path,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
        skip_workflow_runs: bool = False,
        skip_pr_linkages: bool = False,
    ) -> PlanListData:
        """Batch fetch all data needed for plan listing.

        Args:
            repo_root: Repository root directory
            labels: Labels to filter issues by (e.g., ["erk-plan"])
            state: Filter by state ("open", "closed", or None for all)
            limit: Maximum number of issues to return (None for no limit)
            skip_workflow_runs: If True, skip fetching workflow runs (for performance)
            skip_pr_linkages: If True, skip fetching PR linkages (for performance)

        Returns:
            PlanListData containing issues, PR linkages, and workflow runs
        """
        # Fetch issues using GitHubIssues integration
        issues = self._github_issues.list_issues(repo_root, labels=labels, state=state, limit=limit)

        # Extract issue numbers for batch operations
        issue_numbers = [issue.number for issue in issues]

        # Conditionally fetch PR linkages (skip for performance when not needed)
        pr_linkages: dict[int, list[PullRequestInfo]] = {}
        if not skip_pr_linkages and issues:
            # Extract owner/repo from first issue URL
            owner_repo = extract_owner_repo_from_github_url(issues[0].url)
            if owner_repo is not None:
                owner, repo = owner_repo
                pr_linkages = self._github.get_prs_linked_to_issues(
                    repo_root, issue_numbers, owner, repo
                )

        # Conditionally fetch workflow runs (skip for performance when not needed)
        workflow_runs: dict[int, WorkflowRun | None] = {}
        if not skip_workflow_runs:
            # Extract node_ids from plan-header metadata
            node_id_to_issue: dict[str, int] = {}
            for issue in issues:
                _, node_id, _ = extract_plan_header_dispatch_info(issue.body)
                if node_id is not None:
                    node_id_to_issue[node_id] = issue.number

            # Batch fetch workflow runs via GraphQL nodes(ids: [...])
            if node_id_to_issue:
                runs_by_node_id = self._github.get_workflow_runs_by_node_ids(
                    repo_root,
                    list(node_id_to_issue.keys()),
                )
                for node_id, run in runs_by_node_id.items():
                    issue_number = node_id_to_issue[node_id]
                    workflow_runs[issue_number] = run

        return PlanListData(
            issues=issues,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
        )
