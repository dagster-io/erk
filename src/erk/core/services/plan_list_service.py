"""Service for efficiently fetching plan list data via batched API calls.

Uses GraphQL nodes(ids: [...]) for O(1) batch lookup of workflow runs (~200ms for any N).
All plans store last_dispatched_node_id in the plan-header metadata block.

Performance optimization: When PR linkages are needed, uses unified GraphQL query via
get_issues_with_pr_linkages() to fetch issues + PR linkages in a single API call (~600ms),
instead of separate calls for issues (~500ms) and PR linkages (~1500ms).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from erk_shared.core.plan_list_service import PlanListData as PlanListData
from erk_shared.core.plan_list_service import PlanListService
from erk_shared.gateway.github.abc import LocalGitHub
from erk_shared.gateway.github.graphql_queries import GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.metadata.plan_header import extract_plan_header_dispatch_info
from erk_shared.gateway.github.pr_data_parsing import (
    merge_rest_graphql_pr_data,
    parse_workflow_runs_nodes_response,
)
from erk_shared.gateway.github.types import (
    GitHubRepoLocation,
    IssueFilterState,
    WorkflowRun,
)
from erk_shared.gateway.time.abc import Time
from erk_shared.plan_store.conversion import github_issue_to_plan, pr_details_to_plan
from erk_shared.plan_store.planned_pr_lifecycle import (
    extract_plan_content,
    has_original_plan_section,
)

if TYPE_CHECKING:
    from erk_shared.gateway.http.abc import HttpClient


class PlannedPRPlanListService(PlanListService):
    """Plan list service for planned-PR-backed plans.

    Uses a single GraphQL query to fetch draft PRs with the erk-plan label
    along with rich data (checks, review threads, merge status). Converts
    results to PlanListData with fully populated PullRequestInfo for display.
    """

    def __init__(self, github: LocalGitHub, *, time: Time) -> None:
        """Initialize with GitHub gateway.

        Args:
            github: GitHub gateway implementation
            time: Time gateway for monotonic timing
        """
        self._github = github
        self._time = time

    def get_plan_list_data(
        self,
        *,
        location: GitHubRepoLocation,
        labels: list[str],
        state: IssueFilterState = "open",
        limit: int | None = None,
        skip_workflow_runs: bool = False,
        creator: str | None = None,
        exclude_labels: list[str] | None = None,
        http_client: HttpClient,
    ) -> PlanListData:
        """Fetch plan list data from draft PRs via direct HTTP calls.

        Args:
            location: GitHub repository location
            labels: Labels to filter by
            state: Filter by state
            limit: Maximum number of results
            skip_workflow_runs: If True, skip fetching workflow runs
            creator: Filter by PR author username
            exclude_labels: Labels to exclude from results
            http_client: HTTP client for direct API calls

        Returns:
            PlanListData with plans from draft PRs
        """
        return self._get_plan_list_data_http(
            http_client,
            location=location,
            labels=labels,
            state=state,
            limit=limit,
            skip_workflow_runs=skip_workflow_runs,
            creator=creator,
            exclude_labels=exclude_labels,
        )

    def _get_plan_list_data_http(
        self,
        http_client: HttpClient,
        *,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None,
        limit: int | None,
        skip_workflow_runs: bool,
        creator: str | None,
        exclude_labels: list[str] | None,
    ) -> PlanListData:
        """Fetch plan list data via direct HTTP calls (no subprocess overhead).

        Replicates the logic of list_plan_prs_with_details() but uses
        HttpClient.get_list() and HttpClient.graphql() directly.
        """
        repo_id = location.repo_id

        # Step 1: REST issues list with server-side filtering
        rest_state = state.lower() if state else "open"
        effective_limit = limit if limit is not None else 30

        params = [
            f"labels={','.join(labels)}",
            f"state={rest_state}",
            f"per_page={effective_limit}",
            "sort=updated",
            "direction=desc",
        ]
        if creator is not None:
            params.append(f"creator={creator}")

        endpoint = f"repos/{repo_id.owner}/{repo_id.repo}/issues?{'&'.join(params)}"

        t0 = self._time.monotonic()
        issues_data = http_client.get_list(endpoint)

        # Filter to PRs only (items with pull_request key)
        pr_items = [item for item in issues_data if "pull_request" in item]

        # Client-side exclude_labels filtering
        if exclude_labels:
            exclude_set = set(exclude_labels)
            pr_items = [
                item
                for item in pr_items
                if not any(label["name"] in exclude_set for label in item.get("labels", []))
            ]

        if not pr_items:
            t1 = self._time.monotonic()
            return PlanListData(
                plans=[],
                pr_linkages={},
                workflow_runs={},
                api_ms=(t1 - t0) * 1000,
            )

        # Step 2: Batched GraphQL enrichment
        pr_numbers = [item["number"] for item in pr_items]
        enrichment = self._enrich_prs_via_http(http_client, repo_id.owner, repo_id.repo, pr_numbers)

        # Step 3: Merge REST + GraphQL data
        pr_details_list, pr_linkages, unenriched_count = merge_rest_graphql_pr_data(
            pr_items, enrichment, repo_id
        )
        t1 = self._time.monotonic()

        # Step 4: Parse plan content from PR bodies
        plans, node_id_to_plan = self._parse_pr_details(pr_details_list)
        t2 = self._time.monotonic()

        # Step 5: Workflow runs via GraphQL
        workflow_runs = self._fetch_workflow_runs_http(
            http_client, node_id_to_plan, skip_workflow_runs=skip_workflow_runs
        )
        t3 = self._time.monotonic()

        warnings = _build_enrichment_warnings(unenriched_count, len(pr_details_list))

        return PlanListData(
            plans=plans,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
            api_ms=(t1 - t0) * 1000,
            plan_parsing_ms=(t2 - t1) * 1000,
            workflow_runs_ms=(t3 - t2) * 1000,
            warnings=warnings,
        )

    def _enrich_prs_via_http(
        self,
        http_client: HttpClient,
        owner: str,
        repo: str,
        pr_numbers: list[int],
    ) -> dict[int, dict[str, Any]]:
        """Batch-fetch rich PR fields via HttpClient.graphql().

        Builds the same aliased pullRequest(number: N) query as
        RealLocalGitHub._enrich_prs_via_graphql but sends it via HTTP.
        """
        pr_fields = """
            isDraft
            mergeable
            mergeStateStatus
            isCrossRepository
            baseRefName
            headRefName
            statusCheckRollup {
                state
                contexts(last: 1) {
                    totalCount
                    checkRunCountsByState { state count }
                    statusContextCountsByState { state count }
                }
            }
            reviewThreads(first: 100) {
                totalCount
                nodes { isResolved }
            }
            reviewDecision
        """

        aliases = []
        for pr_num in pr_numbers:
            aliases.append(f"pr_{pr_num}: pullRequest(number: {pr_num}) {{ {pr_fields} }}")

        query = (
            "query($owner: String!, $repo: String!) {"
            f"  repository(owner: $owner, name: $repo) {{ {' '.join(aliases)} }}"
            "}"
        )

        response = http_client.graphql(query=query, variables={"owner": owner, "repo": repo})

        repo_data = response.get("data", {}).get("repository", {})
        result: dict[int, dict[str, Any]] = {}
        for pr_num in pr_numbers:
            alias = f"pr_{pr_num}"
            node = repo_data.get(alias)
            if node is not None:
                result[pr_num] = node
        return result

    def _fetch_workflow_runs_http(
        self,
        http_client: HttpClient,
        node_id_to_plan: dict[str, int],
        *,
        skip_workflow_runs: bool,
    ) -> dict[int, WorkflowRun | None]:
        """Fetch workflow runs via HttpClient.graphql()."""
        workflow_runs: dict[int, WorkflowRun | None] = {}
        if skip_workflow_runs or not node_id_to_plan:
            return workflow_runs

        try:
            node_ids = list(node_id_to_plan.keys())
            response = http_client.graphql(
                query=GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY,
                variables={"nodeIds": node_ids},
            )
            runs_by_node_id = parse_workflow_runs_nodes_response(response, node_ids)
            for node_id, run in runs_by_node_id.items():
                workflow_runs[node_id_to_plan[node_id]] = run
        except Exception as e:
            logging.warning("Failed to fetch workflow runs via HTTP: %s", e)

        return workflow_runs

    def _parse_pr_details(
        self,
        pr_details_list: list[Any],
    ) -> tuple[list[Any], dict[str, int]]:
        """Parse PR details into plans and extract dispatch node IDs."""
        plans = []
        node_id_to_plan: dict[str, int] = {}
        for pr_details in pr_details_list:
            plan_body = extract_plan_content(pr_details.body)
            if not has_original_plan_section(pr_details.body):
                if "\n---\n" in plan_body:
                    plan_body = plan_body.rsplit("\n---\n", 1)[0]
            plan = pr_details_to_plan(pr_details, plan_body=plan_body)
            plans.append(plan)

            _, node_id, _ = extract_plan_header_dispatch_info(pr_details.body)
            if node_id is not None:
                node_id_to_plan[node_id] = pr_details.number

        return (plans, node_id_to_plan)

    def _fetch_workflow_runs_subprocess(
        self,
        location: GitHubRepoLocation,
        node_id_to_plan: dict[str, int],
        *,
        skip_workflow_runs: bool,
    ) -> dict[int, WorkflowRun | None]:
        """Fetch workflow runs via subprocess (gh CLI)."""
        workflow_runs: dict[int, WorkflowRun | None] = {}
        if not skip_workflow_runs and node_id_to_plan:
            try:
                runs_by_node_id = self._github.get_workflow_runs_by_node_ids(
                    location.root,
                    list(node_id_to_plan.keys()),
                )
                for node_id, run in runs_by_node_id.items():
                    workflow_runs[node_id_to_plan[node_id]] = run
            except RuntimeError as e:
                logging.warning("Failed to fetch workflow runs: %s", e)
        return workflow_runs


def _build_enrichment_warnings(unenriched_count: int, total_count: int) -> tuple[str, ...]:
    """Build warning messages for degraded GraphQL enrichment data.

    Args:
        unenriched_count: Number of PRs that lacked GraphQL enrichment
        total_count: Total number of PRs fetched

    Returns:
        Tuple of warning strings (empty if no warnings)
    """
    if unenriched_count == 0:
        return ()
    return (
        f"GraphQL enrichment failed for {unenriched_count}/{total_count} PRs "
        "— branch, draft status, and check indicators may be missing",
    )


class RealPlanListService(PlanListService):
    """Service for efficiently fetching plan list data.

    Composes GitHub and GitHubIssues integrations to batch fetch all data
    needed for plan listing. Uses GraphQL nodes(ids: [...]) for efficient
    batch lookup of workflow runs by node_id.
    """

    def __init__(self, github: LocalGitHub, github_issues: GitHubIssues, *, time: Time) -> None:
        """Initialize PlanListService with required integrations.

        Args:
            github: GitHub integration for PR and workflow operations
            github_issues: GitHub issues integration for issue operations
            time: Time gateway for monotonic timing
        """
        self._github = github
        self._github_issues = github_issues
        self._time = time

    def get_plan_list_data(
        self,
        *,
        location: GitHubRepoLocation,
        labels: list[str],
        state: IssueFilterState = "open",
        limit: int | None = None,
        skip_workflow_runs: bool = False,
        creator: str | None = None,
        exclude_labels: list[str] | None = None,
        http_client: HttpClient,
    ) -> PlanListData:
        """Batch fetch all data needed for plan listing.

        Args:
            location: GitHub repository location (local root + repo identity)
            labels: Labels to filter issues by (e.g., ["erk-plan"])
            state: Filter by state ("open" or "closed")
            limit: Maximum number of issues to return (None for no limit)
            skip_workflow_runs: If True, skip fetching workflow runs (for performance)
            creator: Filter by creator username (e.g., "octocat"). If provided,
                only issues created by this user are returned.
            exclude_labels: Labels to exclude from results (label filtering
                is handled server-side by GraphQL)
            http_client: HTTP client (accepted for interface consistency)

        Returns:
            PlanListData containing plans, PR linkages, and workflow runs
        """
        # Always use unified path: issues + PR linkages in one API call (~600ms)
        t0 = self._time.monotonic()
        issues, pr_linkages = self._github.get_issues_with_pr_linkages(
            location=location,
            labels=labels,
            state=state,
            limit=limit,
            creator=creator,
        )
        t1 = self._time.monotonic()

        # Convert IssueInfo to Plan with enriched metadata
        plans = [github_issue_to_plan(issue) for issue in issues]
        t2 = self._time.monotonic()

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
        t3 = self._time.monotonic()

        api_ms = (t1 - t0) * 1000
        plan_parsing_ms = (t2 - t1) * 1000
        workflow_runs_ms = (t3 - t2) * 1000

        return PlanListData(
            plans=plans,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
            api_ms=api_ms,
            plan_parsing_ms=plan_parsing_ms,
            workflow_runs_ms=workflow_runs_ms,
        )
