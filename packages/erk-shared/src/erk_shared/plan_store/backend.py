"""Abstract interface for plan storage backends."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path

from erk_shared.plan_store.types import CreatePlanResult, Plan, PlanQuery


class PlanBackend(ABC):
    """Abstract interface for plan storage operations.

    Implementations provide backend-specific storage for plans.
    Both read and write operations are supported.
    """

    # Read operations (from existing PlanStore)
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
            query: Filter criteria (labels, state, limit)

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

    # Write operations (new)
    @abstractmethod
    def create_plan(
        self,
        repo_root: Path,
        title: str,
        content: str,
        labels: tuple[str, ...],
        metadata: Mapping[str, object],
    ) -> CreatePlanResult:
        """Create a new plan.

        Args:
            repo_root: Repository root directory
            title: Plan title
            content: Plan body/description
            labels: Labels to apply (immutable tuple)
            metadata: Provider-specific fields

        Returns:
            CreatePlanResult with plan_id and url

        Raises:
            RuntimeError: If provider fails
        """
        ...

    @abstractmethod
    def update_metadata(
        self,
        repo_root: Path,
        plan_id: str,
        metadata: Mapping[str, object],
    ) -> None:
        """Update metadata fields on a plan.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier
            metadata: Fields to update

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    @abstractmethod
    def close_plan(self, repo_root: Path, plan_id: str) -> None:
        """Close a plan by its identifier.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    @abstractmethod
    def add_comment(
        self,
        repo_root: Path,
        plan_id: str,
        body: str,
    ) -> str:
        """Add a comment to a plan.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier
            body: Comment body text

        Returns:
            Provider-specific comment identifier

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...
