"""Abstract interface for plan storage providers."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.plan_store.types import CreatePlanResult, Plan, PlanMetadataUpdate, PlanQuery


class PlanStore(ABC):
    """Abstract interface for plan operations.

    All implementations (real and fake) must implement this interface.
    This interface provides both READ and WRITE operations for plans.
    """

    # === READ OPERATIONS ===

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

    # === WRITE OPERATIONS ===

    @abstractmethod
    def create_plan(
        self,
        repo_root: Path,
        title: str,
        body: str,
        labels: list[str],
    ) -> CreatePlanResult:
        """Create a new plan.

        Args:
            repo_root: Repository root directory
            title: Plan title (without [erk-plan] suffix - implementation adds it)
            body: Plan content (markdown)
            labels: Labels to apply (erk-plan added automatically)

        Returns:
            CreatePlanResult with plan_identifier and url

        Raises:
            RuntimeError: If provider fails
        """
        ...

    @abstractmethod
    def update_plan_metadata(
        self,
        repo_root: Path,
        plan_identifier: str,
        updates: PlanMetadataUpdate,
    ) -> None:
        """Update mutable metadata fields in a plan.

        Used for updating worktree_name, last_dispatched_run_id, etc.
        Does NOT update plan content or title.

        Args:
            repo_root: Repository root directory
            plan_identifier: Plan identifier
            updates: Metadata fields to update

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    @abstractmethod
    def ensure_label(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Ensure a label exists in the repository.

        Creates the label if it doesn't exist, no-op if it does.

        Args:
            repo_root: Repository root directory
            label: Label name
            description: Label description
            color: Label color (6-char hex, no #)

        Raises:
            RuntimeError: If provider fails
        """
        ...

    @abstractmethod
    def get_current_user(self) -> str | None:
        """Get the current authenticated user.

        Returns:
            Username or None if not authenticated
        """
        ...
