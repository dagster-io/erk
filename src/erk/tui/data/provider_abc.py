"""TUI data provider ABC for plan table display assembly."""

from abc import ABC, abstractmethod

from erk.tui.data.types import FetchTimings, PlanFilters, PlanRowData, RunRowData
from erk.tui.sorting.types import BranchActivity


class PlanDataProvider(ABC):
    """Abstract base class for TUI plan data assembly.

    Contains only the methods that produce TUI-specific types
    (PlanRowData, FetchTimings, BranchActivity). Domain operations
    (close_plan, dispatch, fetch_content, etc.) live in PlanService.
    """

    @abstractmethod
    def fetch_plans(self, filters: PlanFilters) -> tuple[list[PlanRowData], FetchTimings | None]:
        """Fetch plans matching the given filters.

        Args:
            filters: Filter options for the query

        Returns:
            Tuple of (list of PlanRowData for display, optional FetchTimings breakdown)
        """
        ...

    @abstractmethod
    def fetch_plans_by_ids(self, plan_ids: set[int]) -> list[PlanRowData]:
        """Fetch specific plans by their GitHub numbers.

        Args:
            plan_ids: Set of plan numbers to fetch (issue or PR numbers)

        Returns:
            List of PlanRowData objects for the specified plans, sorted by plan_id
        """
        ...

    @abstractmethod
    def fetch_plans_for_objective(self, objective_issue: int) -> list[PlanRowData]:
        """Fetch plans associated with a specific objective.

        Args:
            objective_issue: The objective issue number to filter by

        Returns:
            List of PlanRowData objects for plans linked to this objective
        """
        ...

    @abstractmethod
    def fetch_runs(self) -> list[RunRowData]:
        """Fetch workflow runs for the Runs tab.

        Returns:
            List of RunRowData for display, sorted by created_at descending
        """
        ...

    @abstractmethod
    def fetch_branch_activity(self, rows: list[PlanRowData]) -> dict[int, BranchActivity]:
        """Fetch branch activity for plans that exist locally.

        Args:
            rows: List of plan rows to fetch activity for

        Returns:
            Mapping of plan_id to BranchActivity for plans with local worktrees.
        """
        ...
