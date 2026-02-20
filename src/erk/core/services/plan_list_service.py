"""Service for efficiently fetching plan list data via batched API calls.

Uses GraphQL nodes(ids: [...]) for O(1) batch lookup of workflow runs (~200ms for any N).
All plan issues store last_dispatched_node_id in the plan-header metadata block.

Performance optimization: When PR linkages are needed, uses unified GraphQL query via
get_issues_with_pr_linkages() to fetch issues + PR linkages in a single API call (~600ms),
instead of separate calls for issues (~500ms) and PR linkages (~1500ms).
"""

import logging

from erk_shared.core.plan_list_service import PlanListData as PlanListData
from erk_shared.core.plan_list_service import PlanListService
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.plan_header import extract_plan_header_dispatch_info
from erk_shared.gateway.github.types import (
    GitHubRepoLocation,
    WorkflowRun,
)
from erk_shared.plan_store.conversion import issue_info_to_plan, pr_details_to_plan
from erk_shared.plan_store.draft_pr_lifecycle import (
    extract_plan_content,
    has_original_plan_section,
)

_PLAN_LABEL = "erk-plan"


class DraftPRPlanListService(PlanListService):
    """Plan list service for draft-PR-backed plans.

    Uses a single GraphQL query to fetch draft PRs with the erk-plan label
    along with rich data (checks, review threads, merge status). Converts
    results to PlanListData with fully populated PullRequestInfo for display.
    """

    def __init__(self, github: GitHub) -> None:
        """Initialize with GitHub gateway.

        Args:
            github: GitHub gateway implementation
        """
        self._github = github

    def get_plan_list_data(
        self,
        *,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
        skip_workflow_runs: bool = False,
        creator: str | None = None,
    ) -> PlanListData:
        """Fetch plan list data from draft PRs via single GraphQL call.

        Uses list_plan_prs_with_details() to get PRDetails (for plan content)
        and PullRequestInfo (with checks, review threads, merge status) in one
        API call. Workflow runs are fetched separately via batch GraphQL lookup.

        Args:
            location: GitHub repository location
            labels: Labels to filter by
            state: Filter by state
            limit: Maximum number of results
            skip_workflow_runs: If True, skip fetching workflow runs
            creator: Filter by PR author username

        Returns:
            PlanListData with plans from draft PRs
        """
        all_labels = [_PLAN_LABEL, *labels]

        # Single GraphQL call returns both PRDetails and rich PullRequestInfo
        pr_details_list, pr_linkages = self._github.list_plan_prs_with_details(
            location,
            labels=all_labels,
            state=state,
            limit=limit,
            author=creator,
        )

        plans = []
        node_id_to_plan: dict[str, int] = {}
        for pr_details in pr_details_list:
            plan_body = extract_plan_content(pr_details.body)
            # extract_plan_content falls back to content-after-separator for bodies
            # without <details>original-plan</details>. For rewritten PRs this
            # includes the footer (Closes + checkout). Strip it by removing
            # everything after the last \n---\n footer delimiter.
            if not has_original_plan_section(pr_details.body):
                if "\n---\n" in plan_body:
                    plan_body = plan_body.rsplit("\n---\n", 1)[0]
            plan = pr_details_to_plan(pr_details, plan_body=plan_body)
            plans.append(plan)

            # Capture dispatch node_id for workflow run batch fetch
            _, node_id, _ = extract_plan_header_dispatch_info(pr_details.body)
            if node_id is not None:
                node_id_to_plan[node_id] = pr_details.number

        workflow_runs: dict[int, WorkflowRun | None] = {}
        if not skip_workflow_runs and node_id_to_plan:
            try:
                runs_by_node_id = self._github.get_workflow_runs_by_node_ids(
                    location.root,
                    list(node_id_to_plan.keys()),
                )
                for node_id, run in runs_by_node_id.items():
                    workflow_runs[node_id_to_plan[node_id]] = run
            except Exception as e:
                logging.warning("Failed to fetch workflow runs: %s", e)

        return PlanListData(
            plans=plans,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
        )


class RealPlanListService(PlanListService):
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
        creator: str | None = None,
    ) -> PlanListData:
        """Batch fetch all data needed for plan listing.

        Args:
            location: GitHub repository location (local root + repo identity)
            labels: Labels to filter issues by (e.g., ["erk-plan"])
            state: Filter by state ("open", "closed", or None for all)
            limit: Maximum number of issues to return (None for no limit)
            skip_workflow_runs: If True, skip fetching workflow runs (for performance)
            creator: Filter by creator username (e.g., "octocat"). If provided,
                only issues created by this user are returned.

        Returns:
            PlanListData containing plans, PR linkages, and workflow runs
        """
        # Always use unified path: issues + PR linkages in one API call (~600ms)
        issues, pr_linkages = self._github.get_issues_with_pr_linkages(
            location=location,
            labels=labels,
            state=state,
            limit=limit,
            creator=creator,
        )

        # Convert IssueInfo to Plan with enriched metadata
        plans = [issue_info_to_plan(issue) for issue in issues]

        # Conditionally fetch workflow runs (skip for performance when not needed)
        workflow_runs: dict[int, WorkflowRun | None] = {}
        if not skip_workflow_runs:
            # Extract node_ids from plan-header metadata (still from issue body)
            node_id_to_issue: dict[str, int] = {}
            for issue in issues:
                _, node_id, _ = extract_plan_header_dispatch_info(issue.body)
                if node_id is not None:
                    node_id_to_issue[node_id] = issue.number

            # Batch fetch workflow runs via GraphQL nodes(ids: [...])
            if node_id_to_issue:
                try:
                    runs_by_node_id = self._github.get_workflow_runs_by_node_ids(
                        location.root,
                        list(node_id_to_issue.keys()),
                    )
                    for node_id, run in runs_by_node_id.items():
                        issue_number = node_id_to_issue[node_id]
                        workflow_runs[issue_number] = run
                except Exception as e:
                    # Network/API failure - continue without workflow run data
                    # Dashboard will show "-" for run columns, which is acceptable
                    logging.warning("Failed to fetch workflow runs: %s", e)

        return PlanListData(
            plans=plans,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
        )
