"""Abstract interface for plan storage backends.

PlanBackend is a BACKEND, not a gateway. Backends compose gateways (like GitHubIssues)
and should NOT have fake implementations. To test code that uses a PlanBackend,
inject fake gateways into the real backend implementation.

Example:
    # Testing with fake gateway
    fake_issues = FakeGitHubIssues()
    backend = GitHubPlanBackend(fake_issues)  # Real backend, fake gateway
    result = backend.create_plan(...)

    # Assert on gateway mutations
    assert fake_issues.created_issues[0][0] == "expected title"

See: .claude/skills/fake-driven-testing/references/gateway-architecture.md
for the full gateway vs backend architecture.
"""

from abc import abstractmethod
from collections.abc import Mapping
from pathlib import Path

from erk_shared.plan_store.store import PlanStore
from erk_shared.plan_store.types import CreatePlanResult, Plan, PlanQuery


class PlanBackend(PlanStore):
    """Abstract interface for plan storage operations.

    Extends PlanStore to add write operations while maintaining backward
    compatibility with code that only needs read operations.

    Implementations provide backend-specific storage for plans.
    Both read and write operations are supported.

    Read operations (inherited from PlanStore):
        get_plan: Fetch a plan by identifier
        list_plans: Query plans by criteria
        get_provider_name: Get the provider name
        close_plan: Close a plan

    Write operations (added by PlanBackend):
        create_plan: Create a new plan
        update_metadata: Update plan metadata
        add_comment: Add a comment to a plan
    """

    # Read operations (inherited from PlanStore, re-declared with updated param names)

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

    # Write operations

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
            metadata: Provider-specific metadata

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
        """Update plan metadata.

        Args:
            repo_root: Repository root directory
            plan_id: Provider-specific identifier
            metadata: New metadata to set

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    # close_plan is inherited from PlanStore

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
            Comment ID as string

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...
