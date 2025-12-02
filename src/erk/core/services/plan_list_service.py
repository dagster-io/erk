"""Service for efficiently fetching plan list data via batched API calls.

Uses GraphQL nodes(ids: [...]) for O(1) batch lookup of workflow runs (~200ms for any N).
All plan issues store last_dispatched_node_id in the plan-header metadata block.

Performance optimization: When PR linkages are needed, uses unified GraphQL query via
get_issues_with_pr_linkages() to fetch issues + PR linkages in a single API call (~600ms),
instead of separate calls for issues (~500ms) and PR linkages (~1500ms).
"""

from dataclasses import dataclass

from erk_shared.github.abc import GitHub
from erk_shared.github.issues import GitHubIssues, IssueInfo
from erk_shared.github.metadata import extract_plan_header_dispatch_info
from erk_shared.github.types import GitHubRepoLocation, PullRequestInfo, WorkflowRun


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
        *,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
        skip_workflow_runs: bool = False,
    ) -> PlanListData:
        """Batch fetch all data needed for plan listing.

        Args:
            location: GitHub repository location (local root + repo identity)
            labels: Labels to filter issues by (e.g., ["erk-plan"])
            state: Filter by state ("open", "closed", or None for all)
            limit: Maximum number of issues to return (None for no limit)
            skip_workflow_runs: If True, skip fetching workflow runs (for performance)

        Returns:
            PlanListData containing issues, PR linkages, and workflow runs
        """
        # Always use unified path: issues + PR linkages in one API call (~600ms)
        issues, pr_linkages = self._github.get_issues_with_pr_linkages(
            location,
            labels,
            state=state,
            limit=limit,
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
                    location.root,
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
