"""Real implementation of ObjectiveListService.

Fetches objectives directly from GitHub issues with hardcoded
labels=["erk-objective"]. Objectives are always GitHub issues regardless
of the configured plan backend.
"""

import logging

from erk_shared.core.objective_list_service import ObjectiveListService
from erk_shared.core.plan_list_service import PlanListData
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.metadata.plan_header import extract_plan_header_dispatch_info
from erk_shared.gateway.github.types import GitHubRepoLocation, IssueFilterState, WorkflowRun
from erk_shared.gateway.time.abc import Time
from erk_shared.plan_store.conversion import issue_info_to_plan

_OBJECTIVE_LABEL = "erk-objective"


class RealObjectiveListService(ObjectiveListService):
    """Fetches objectives directly from GitHub issues.

    Calls the GitHub gateway directly with hardcoded objective label,
    because objectives are GitHub issues regardless of the plan backend.
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
    ) -> PlanListData:
        t = self._time.monotonic()
        issues, pr_linkages = self._github.get_issues_with_pr_linkages(
            location=location,
            labels=[_OBJECTIVE_LABEL],
            state=state,
            limit=limit,
            creator=creator,
        )
        api_ms = (self._time.monotonic() - t) * 1000

        t = self._time.monotonic()
        plans = [issue_info_to_plan(issue) for issue in issues]
        plan_parsing_ms = (self._time.monotonic() - t) * 1000

        t = self._time.monotonic()
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
        workflow_runs_ms = (self._time.monotonic() - t) * 1000

        return PlanListData(
            plans=plans,
            pr_linkages=pr_linkages,
            workflow_runs=workflow_runs,
            api_ms=api_ms,
            plan_parsing_ms=plan_parsing_ms,
            workflow_runs_ms=workflow_runs_ms,
        )
