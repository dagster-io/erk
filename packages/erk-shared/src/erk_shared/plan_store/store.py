"""Abstract interface for plan storage providers.

DEPRECATED: Use PlanBackend instead. PlanStore is a read-only subset of PlanBackend
and is retained only for backward compatibility with existing type annotations.
New code should use PlanBackend for full read/write access.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.plan_store.types import Plan, PlanQuery


class PlanStore(ABC):
    """Abstract interface for plan read operations.

    DEPRECATED: Use PlanBackend for new code. PlanBackend provides the full
    read/write interface including create_plan(), update_metadata(), and add_comment().

    This interface is retained for backward compatibility with code that only needs
    read operations (get_plan, list_plans, get_provider_name, close_plan).
    """

    @abstractmethod
    def get_plan(self, repo_root: Path, plan_id: str) -> Plan:
        """Fetch a plan by identifier.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier (e.g., "42", "PROJ-123")

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
    def close_plan(self, repo_root: Path, plan_id: str) -> None:
        """Close a plan by its identifier (issue number or GitHub URL).

        Args:
            repo_root: Repository root directory
            plan_id: Plan identifier (issue number like "123" or GitHub URL)

        Raises:
            RuntimeError: If provider fails, plan not found, or invalid identifier
        """
        ...
