"""TUI data provider ABC for plan table display assembly."""

from abc import ABC, abstractmethod

from erk.tui.data.types import FetchTimings, PrFilters, PrRowData, RunRowData
from erk.tui.sorting.types import BranchActivity


class PrDataProvider(ABC):
    """Abstract base class for TUI plan data assembly.

    Contains only the methods that produce TUI-specific types
    (PrRowData, FetchTimings, BranchActivity). Domain operations
    (close_pr, dispatch, fetch_content, etc.) live in PrService.
    """

    @abstractmethod
    def fetch_prs(self, filters: PrFilters) -> tuple[list[PrRowData], FetchTimings | None]:
        """Fetch plans matching the given filters.

        Args:
            filters: Filter options for the query

        Returns:
            Tuple of (list of PrRowData for display, optional FetchTimings breakdown)
        """
        ...

    @abstractmethod
    def fetch_prs_by_ids(self, pr_ids: set[int]) -> list[PrRowData]:
        """Fetch specific plans by their GitHub numbers.

        Args:
            pr_ids: Set of plan numbers to fetch (issue or PR numbers)

        Returns:
            List of PrRowData objects for the specified plans, sorted by pr_number
        """
        ...

    @abstractmethod
    def fetch_prs_for_objective(self, objective_issue: int) -> list[PrRowData]:
        """Fetch plans associated with a specific objective.

        Args:
            objective_issue: The objective issue number to filter by

        Returns:
            List of PrRowData objects for plans linked to this objective
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
    def fetch_branch_activity(self, rows: list[PrRowData]) -> dict[int, BranchActivity]:
        """Fetch branch activity for plans that exist locally.

        Args:
            rows: List of plan rows to fetch activity for

        Returns:
            Mapping of pr_number to BranchActivity for plans with local worktrees.
        """
        ...
