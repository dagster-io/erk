"""Real implementation of ObjectiveListService.

Objectives are GitHub issues with the 'erk-objective' label. This service
fetches them directly via the GitHub gateway's unified issue+PR-linkage
query, without going through any plan list service.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from erk_shared.core.objective_list_service import ObjectiveListService
from erk_shared.core.plan_list_service import PlanListData
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.metadata.plan_header import extract_plan_header_dispatch_info
from erk_shared.gateway.github.types import (
    GitHubRepoLocation,
    IssueFilterState,
    WorkflowRun,
)
from erk_shared.gateway.time.abc import Time
from erk_shared.plan_store.conversion import github_issue_to_plan

if TYPE_CHECKING:
    from erk_shared.gateway.http.abc import HttpClient

_OBJECTIVE_LABEL = "erk-objective"


class RealObjectiveListService(ObjectiveListService):
    """Fetches objectives directly via GitHub issue APIs.

    Objectives are GitHub issues (not PRs), so this service uses
    get_issues_with_pr_linkages with the erk-objective label, then
    converts via github_issue_to_plan.
    """

    def __init__(self, github: GitHub, *, time: Time) -> None:
        self._github = github
        self._time = time

    def get_objective_list_data(
        self,
        *,
        location: GitHubRepoLocation,
        state: IssueFilterState = "open",
        limit: int | None = None,
        skip_workflow_runs: bool = False,
        creator: str | None = None,
        exclude_labels: list[str] | None = None,
        http_client: HttpClient,
    ) -> PlanListData:
        t0 = self._time.monotonic()
        issues, pr_linkages = self._github.get_issues_with_pr_linkages(
            location=location,
            labels=[_OBJECTIVE_LABEL],
            state=state,
            limit=limit,
            creator=creator,
        )
        t1 = self._time.monotonic()

        plans = [github_issue_to_plan(issue) for issue in issues]
        t2 = self._time.monotonic()

        workflow_runs: dict[int, WorkflowRun | None] = {}
        if not skip_workflow_runs:
            node_id_to_issue: dict[str, int] = {}
            for issue in issues:
                _, node_id, _ = extract_plan_header_dispatch_info(issue.body)
                if node_id is not None:
                    node_id_to_issue[node_id] = issue.number

            if node_id_to_issue:
                try:
                    runs_by_node_id = self._github.get_workflow_runs_by_node_ids(
                        location.root,
                        list(node_id_to_issue.keys()),
                    )
                    for node_id, run in runs_by_node_id.items():
                        workflow_runs[node_id_to_issue[node_id]] = run
                except RuntimeError as e:
                    logging.warning("Failed to fetch workflow runs: %s", e)
        t3 = self._time.monotonic()

        return PlanListData(
            plans=plans,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
            api_ms=(t1 - t0) * 1000,
            plan_parsing_ms=(t2 - t1) * 1000,
            workflow_runs_ms=(t3 - t2) * 1000,
        )
