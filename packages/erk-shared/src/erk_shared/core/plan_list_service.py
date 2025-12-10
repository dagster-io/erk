"""Plan list service abstraction - ABC and types.

This module provides the abstract interface for efficiently fetching plan list data.
The real implementation remains in erk.core.services.plan_list_service.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from erk_shared.github.issues import IssueInfo
from erk_shared.github.types import GitHubRepoLocation, PullRequestInfo, WorkflowRun


@dataclass(frozen=True)
class PlanListData:
    """Combined data for plan listing.

    Attributes:
        issues: List of IssueInfo objects
        pr_linkages: Mapping of issue_number -> list of PRs that close that issue
        workflow_runs: Mapping of issue_number -> most relevant WorkflowRun
    """

    issues: list[IssueInfo]
    pr_linkages: dict[int, list[PullRequestInfo]]
    workflow_runs: dict[int, WorkflowRun | None]


class PlanListService(ABC):
    """Abstract interface for efficiently fetching plan list data.

    Composes GitHub and GitHubIssues integrations to batch fetch all data
    needed for plan listing. Uses GraphQL nodes(ids: [...]) for efficient
    batch lookup of workflow runs by node_id.
    """

    @abstractmethod
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
            PlanListData containing issues, PR linkages, and workflow runs
        """
        ...
