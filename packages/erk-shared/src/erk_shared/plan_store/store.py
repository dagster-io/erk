"""Abstract interface for plan storage providers.

DEPRECATED: This module contains PlanStore which is deprecated in favor of
PlanBackend (see backend.py). PlanStore will be removed after Phase 3 migration
when GitHubPlanStore is refactored to GitHubPlanBackend.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.plan_store.types import Plan, PlanQuery


class PlanStore(ABC):
    """Abstract interface for plan operations.

    DEPRECATED: Use PlanBackend instead. This interface only supports read
    operations. PlanBackend provides the complete interface with both read
    and write operations.

    This interface will be removed after Phase 3 migration.
    """

    @abstractmethod
    def get_plan(self, repo_root: Path, plan_identifier: str) -> Plan:
        """Fetch a plan by identifier.

        Args:
            repo_root: Repository root directory
            plan_identifier: Provider-specific identifier (e.g., "42", "PROJ-123")

        Returns:
            Plan with all metadata

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    @abstractmethod
    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        """Query plans by criteria.

        Args:
            repo_root: Repository root directory
            query: Filter criteria (labels, state, assignee, limit)

        Returns:
            List of Plan matching the criteria

        Raises:
            RuntimeError: If provider fails
        """
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the provider.

        Returns:
            Provider name (e.g., "github", "gitlab", "linear")
        """
        ...

    @abstractmethod
    def close_plan(self, repo_root: Path, identifier: str) -> None:
        """Close a plan by its identifier (issue number or GitHub URL).

        Args:
            repo_root: Repository root directory
            identifier: Plan identifier (issue number like "123" or GitHub URL)

        Raises:
            RuntimeError: If provider fails, plan not found, or invalid identifier
        """
        ...
