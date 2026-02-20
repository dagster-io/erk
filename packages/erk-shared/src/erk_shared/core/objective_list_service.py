"""Objective list service abstraction - ABC for fetching objective list data.

Symmetric with PlanListService but encapsulates the knowledge that objectives
are GitHub issues with the 'erk-objective' label. No labels parameter is exposed.
"""

from abc import ABC, abstractmethod

from erk_shared.core.plan_list_service import PlanListData
from erk_shared.gateway.github.types import GitHubRepoLocation


class ObjectiveListService(ABC):
    """Abstract interface for fetching objective list data.

    Unlike PlanListService, this has no labels parameter — the implementation
    knows that objectives use the 'erk-objective' label internally.
    """

    @abstractmethod
    def get_objective_list_data(
        self,
        *,
        location: GitHubRepoLocation,
        state: str | None = None,
        limit: int | None = None,
        skip_workflow_runs: bool = False,
        creator: str | None = None,
    ) -> PlanListData:
        """Fetch all data needed for objective listing.

        Args:
            location: GitHub repository location (local root + repo identity)
            state: Filter by state ("open", "closed", or None for all)
            limit: Maximum number of objectives to return (None for no limit)
            skip_workflow_runs: If True, skip fetching workflow runs (for performance)
            creator: Filter by creator username

        Returns:
            PlanListData containing objectives as plans, PR linkages, and workflow runs
        """
        ...
