"""In-memory fake implementation of PlanBackend for testing."""

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.plan_store.backend import PlanBackend
from erk_shared.plan_store.types import CreatePlanResult, Plan, PlanQuery, PlanState


class FakePlanBackend(PlanBackend):
    """In-memory fake implementation for testing.

    All state is provided via constructor using keyword arguments.
    """

    def __init__(
        self,
        *,
        plans: dict[str, Plan] | None,
        next_plan_id: int,
        provider_name: str,
    ) -> None:
        """Create FakePlanBackend with pre-configured state.

        Args:
            plans: Mapping of plan_id -> Plan (None for empty dict)
            next_plan_id: Next plan ID to assign (for predictable testing)
            provider_name: Name to return from get_provider_name()
        """
        self._plans: dict[str, Plan] = plans if plans is not None else {}
        self._next_plan_id = next_plan_id
        self._provider_name = provider_name
        # Mutation tracking
        self._created_plans: list[tuple[str, str, tuple[str, ...]]] = []
        self._updated_metadata: list[tuple[str, Mapping[str, object]]] = []
        self._closed_plans: list[str] = []
        self._added_comments: list[tuple[str, str, str]] = []
        self._next_comment_id = 1000

    # Read-only properties for test assertions
    @property
    def created_plans(self) -> list[tuple[str, str, tuple[str, ...]]]:
        """Read-only access to created plans for test assertions.

        Returns list of (title, content, labels) tuples.
        """
        return self._created_plans

    @property
    def updated_metadata(self) -> list[tuple[str, Mapping[str, object]]]:
        """Read-only access to updated metadata for test assertions.

        Returns list of (plan_id, metadata) tuples.
        """
        return self._updated_metadata

    @property
    def closed_plans(self) -> list[str]:
        """Read-only access to closed plans for test assertions.

        Returns list of plan_ids that were closed.
        """
        return self._closed_plans

    @property
    def added_comments(self) -> list[tuple[str, str, str]]:
        """Read-only access to added comments for test assertions.

        Returns list of (plan_id, body, comment_id) tuples.
        """
        return self._added_comments

    # PlanBackend implementation

    def get_plan(self, repo_root: Path, plan_id: str) -> Plan:
        """Get plan from fake storage.

        Raises:
            RuntimeError: If plan_id not found
        """
        if plan_id not in self._plans:
            msg = f"Plan #{plan_id} not found"
            raise RuntimeError(msg)
        return self._plans[plan_id]

    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        """Query plans from fake storage.

        Filters by labels (AND logic), state, and limit.
        """
        plans = list(self._plans.values())

        # Filter by labels (AND logic - plan must have ALL specified labels)
        if query.labels:
            label_set = set(query.labels)
            plans = [plan for plan in plans if label_set.issubset(set(plan.labels))]

        # Filter by state
        if query.state is not None:
            plans = [plan for plan in plans if plan.state == query.state]

        # Apply limit
        if query.limit is not None:
            plans = plans[: query.limit]

        return plans

    def get_provider_name(self) -> str:
        """Return configured provider name."""
        return self._provider_name

    def create_plan(
        self,
        repo_root: Path,
        title: str,
        content: str,
        labels: tuple[str, ...],
        metadata: Mapping[str, object],
    ) -> CreatePlanResult:
        """Create plan in fake storage and track mutation."""
        plan_id = str(self._next_plan_id)
        self._next_plan_id += 1

        # Create realistic fake URL for testing
        url = f"https://fake.example.com/plans/{plan_id}"

        now = datetime.now(UTC)
        self._plans[plan_id] = Plan(
            plan_identifier=plan_id,
            title=title,
            body=content,
            state=PlanState.OPEN,
            url=url,
            labels=list(labels),
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata=dict(metadata),
        )
        self._created_plans.append((title, content, labels))

        return CreatePlanResult(plan_id=plan_id, url=url)

    def update_metadata(
        self,
        repo_root: Path,
        plan_id: str,
        metadata: Mapping[str, object],
    ) -> None:
        """Track metadata update mutation.

        Raises:
            RuntimeError: If plan_id not found
        """
        if plan_id not in self._plans:
            msg = f"Plan #{plan_id} not found"
            raise RuntimeError(msg)
        self._updated_metadata.append((plan_id, metadata))

    def close_plan(self, repo_root: Path, plan_id: str) -> None:
        """Close plan in fake storage and track mutation.

        Raises:
            RuntimeError: If plan_id not found
        """
        if plan_id not in self._plans:
            msg = f"Plan #{plan_id} not found"
            raise RuntimeError(msg)

        # Update plan state to closed
        current_plan = self._plans[plan_id]
        self._plans[plan_id] = Plan(
            plan_identifier=current_plan.plan_identifier,
            title=current_plan.title,
            body=current_plan.body,
            state=PlanState.CLOSED,
            url=current_plan.url,
            labels=current_plan.labels,
            assignees=current_plan.assignees,
            created_at=current_plan.created_at,
            updated_at=datetime.now(UTC),
            metadata=current_plan.metadata,
        )
        self._closed_plans.append(plan_id)

    def add_comment(
        self,
        repo_root: Path,
        plan_id: str,
        body: str,
    ) -> str:
        """Record comment in mutation tracking and return generated comment ID.

        Raises:
            RuntimeError: If plan_id not found
        """
        if plan_id not in self._plans:
            msg = f"Plan #{plan_id} not found"
            raise RuntimeError(msg)
        comment_id = str(self._next_comment_id)
        self._next_comment_id += 1
        self._added_comments.append((plan_id, body, comment_id))
        return comment_id
