"""Pure parsing functions for GitHub PR and workflow data.

Extracted from RealLocalGitHub to enable reuse by both the subprocess path
(via RealLocalGitHub methods) and the direct HTTP path (via PlannedPRPlanListService).

All functions are stateless — they transform data without side effects.
"""

from datetime import datetime
from typing import Any

from erk_shared.gateway.github.parsing import parse_aggregated_check_counts
from erk_shared.gateway.github.types import (
    BRANCH_NOT_AVAILABLE,
    DISPLAY_TITLE_NOT_AVAILABLE,
    GitHubRepoId,
    MergeableStatus,
    PRDetails,
    PullRequestInfo,
    StatusCheckRollupData,
    WorkflowRun,
    WorkflowRunConclusion,
    WorkflowRunStatus,
)


def parse_status_rollup(
    status_rollup: StatusCheckRollupData | None,
) -> tuple[bool | None, tuple[int, int] | None]:
    """Parse checks status and counts from statusCheckRollup.

    Returns (checks_passing, checks_counts).
    """
    if status_rollup is None:
        return (None, None)

    rollup_state = status_rollup.get("state")
    checks_passing = None
    if rollup_state == "SUCCESS":
        checks_passing = True
    elif rollup_state in ("FAILURE", "ERROR"):
        checks_passing = False

    checks_counts = None
    contexts = status_rollup.get("contexts")
    if contexts is not None and isinstance(contexts, dict):
        total = contexts.get("totalCount", 0)
        if total > 0:
            checks_counts = parse_aggregated_check_counts(
                contexts.get("checkRunCountsByState", []),
                contexts.get("statusContextCountsByState", []),
                total,
            )

    return (checks_passing, checks_counts)


def parse_mergeable_status(mergeable: MergeableStatus | None) -> bool | None:
    """Parse has_conflicts from mergeable field."""
    if mergeable == "CONFLICTING":
        return True
    if mergeable == "MERGEABLE":
        return False
    return None


def parse_review_thread_counts(
    review_threads: dict[str, Any] | None,
) -> tuple[int, int] | None:
    """Parse review thread counts from reviewThreads field.

    Returns (resolved_count, total_count) or None if not available.
    """
    if review_threads is None:
        return None

    total_count = review_threads.get("totalCount", 0)
    if total_count == 0:
        return (0, 0)

    nodes = review_threads.get("nodes", [])
    resolved_count = sum(1 for node in nodes if node and node.get("isResolved", False))

    return (resolved_count, total_count)


def merge_rest_graphql_pr_data(
    rest_items: list[dict[str, Any]],
    enrichment: dict[int, dict[str, Any]],
    repo_id: GitHubRepoId,
) -> tuple[list[PRDetails], dict[int, list[PullRequestInfo]], int]:
    """Merge REST issue data with GraphQL PR enrichment into PRDetails and PullRequestInfo.

    Args:
        rest_items: Raw REST API issue/PR items
        enrichment: GraphQL enrichment data keyed by PR number
        repo_id: GitHub repository identity

    Returns:
        Tuple of (pr_details_list, pr_linkages_by_pr_number, unenriched_count).
        PRs without GraphQL enrichment data are included in pr_details_list
        (needed for plan conversion) but excluded from pr_linkages to avoid
        misleading fallback defaults for branch, draft status, and checks.
    """
    pr_details_list: list[PRDetails] = []
    pr_linkages: dict[int, list[PullRequestInfo]] = {}
    unenriched_count = 0

    for item in rest_items:
        pr_number = item["number"]
        gql = enrichment.get(pr_number, {})

        rest_head_ref = item.get("pull_request", {}).get("head", {}).get("ref", "")
        head_ref_name = gql.get("headRefName", rest_head_ref)
        base_ref_name = gql.get("baseRefName", "")
        pr_state = item.get("state", "open").upper()

        pr_details = PRDetails(
            number=pr_number,
            url=item.get("html_url", ""),
            title=item.get("title", ""),
            body=item.get("body", "") or "",
            state=pr_state,
            is_draft=gql.get("isDraft", False),
            base_ref_name=base_ref_name,
            head_ref_name=head_ref_name,
            is_cross_repository=gql.get("isCrossRepository", False),
            mergeable=gql.get("mergeable", "UNKNOWN"),
            merge_state_status=gql.get("mergeStateStatus", "UNKNOWN"),
            owner=repo_id.owner,
            repo=repo_id.repo,
            labels=tuple(label["name"] for label in item.get("labels", [])),
            created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
            author=item.get("user", {}).get("login", ""),
        )
        pr_details_list.append(pr_details)

        # Only create PullRequestInfo when enrichment data is available.
        # Without GraphQL data, fields like base_ref_name, is_draft, and checks
        # would have misleading fallback defaults.
        if not gql:
            unenriched_count += 1
            continue

        # Build PullRequestInfo with rich GraphQL data
        checks_passing, checks_counts = parse_status_rollup(gql.get("statusCheckRollup"))
        has_conflicts = parse_mergeable_status(gql.get("mergeable"))
        review_thread_counts = parse_review_thread_counts(gql.get("reviewThreads"))
        review_decision = gql.get("reviewDecision")

        pr_info = PullRequestInfo(
            number=pr_number,
            state=pr_state,
            url=item.get("html_url", ""),
            is_draft=pr_details.is_draft,
            title=item.get("title"),
            checks_passing=checks_passing,
            owner=repo_id.owner,
            repo=repo_id.repo,
            has_conflicts=has_conflicts,
            checks_counts=checks_counts,
            review_thread_counts=review_thread_counts,
            head_branch=head_ref_name,
            review_decision=review_decision,
            base_ref_name=base_ref_name,
        )
        pr_linkages[pr_number] = [pr_info]

    return (pr_details_list, pr_linkages, unenriched_count)


def parse_workflow_runs_nodes_response(
    response: dict[str, Any],
    node_ids: list[str],
) -> dict[str, WorkflowRun | None]:
    """Parse GraphQL nodes response into WorkflowRun objects.

    Maps the GraphQL checkSuite status/conclusion to WorkflowRun fields.

    Args:
        response: GraphQL response data
        node_ids: Original list of node IDs (for result ordering)

    Returns:
        Mapping of node_id -> WorkflowRun or None
    """
    status_map: dict[str | None, WorkflowRunStatus] = {
        "COMPLETED": "completed",
        "IN_PROGRESS": "in_progress",
        "QUEUED": "queued",
    }
    conclusion_map: dict[str | None, WorkflowRunConclusion] = {
        "SUCCESS": "success",
        "FAILURE": "failure",
        "SKIPPED": "skipped",
        "CANCELLED": "cancelled",
    }

    result: dict[str, WorkflowRun | None] = {}
    nodes = response.get("data", {}).get("nodes", [])

    for node in nodes:
        if node is None:
            continue

        node_id = node.get("id")
        if node_id is None:
            continue

        check_suite = node.get("checkSuite")
        status: WorkflowRunStatus | None = None
        conclusion: WorkflowRunConclusion | None = None
        head_sha: str | None = None

        if check_suite is not None:
            status = status_map.get(check_suite.get("status"))
            conclusion = conclusion_map.get(check_suite.get("conclusion"))

            commit = check_suite.get("commit")
            if commit is not None:
                head_sha = commit.get("oid")

        # Parse created_at timestamp
        created_at = None
        created_at_str = node.get("createdAt")
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

        workflow_run = WorkflowRun(
            run_id=str(node.get("databaseId", "")),
            status=status or "unknown",  # Default for missing status
            conclusion=conclusion,
            branch=BRANCH_NOT_AVAILABLE,
            head_sha=head_sha or "",  # Default for missing SHA
            display_title=DISPLAY_TITLE_NOT_AVAILABLE,
            created_at=created_at,
        )
        result[node_id] = workflow_run

    # Ensure all requested node_ids are in result (with None for missing)
    for node_id in node_ids:
        if node_id not in result:
            result[node_id] = None

    return result
