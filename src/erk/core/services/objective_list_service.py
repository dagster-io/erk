"""Real implementation of ObjectiveListService.

Wraps RealPlanListService with hardcoded labels=["erk-objective"] so that
objectives are always fetched via the issue-based path regardless of the
configured plan backend (draft PR vs issue).
"""

from erk.core.services.plan_list_service import RealPlanListService
from erk_shared.core.objective_list_service import ObjectiveListService
from erk_shared.core.plan_list_service import PlanListData
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.types import GitHubRepoLocation

_OBJECTIVE_LABEL = "erk-objective"


class RealObjectiveListService(ObjectiveListService):
    """Fetches objectives via RealPlanListService with hardcoded objective label.

    Always uses the issue-based RealPlanListService, not DraftPRPlanListService,
    because objectives are GitHub issues regardless of the plan backend.
    """

    def __init__(self, github: GitHub, github_issues: GitHubIssues) -> None:
        self._plan_list_service = RealPlanListService(github, github_issues)

    def get_objective_list_data(
        self,
        *,
        location: GitHubRepoLocation,
        state: str | None = None,
        limit: int | None = None,
        skip_workflow_runs: bool = False,
        creator: str | None = None,
    ) -> PlanListData:
        return self._plan_list_service.get_plan_list_data(
            location=location,
            labels=[_OBJECTIVE_LABEL],
            state=state,
            limit=limit,
            skip_workflow_runs=skip_workflow_runs,
            creator=creator,
        )
