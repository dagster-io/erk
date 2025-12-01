"""In-memory fake implementation for plan storage."""

from datetime import UTC, datetime
from pathlib import Path

from erk_shared.plan_store.store import PlanStore
from erk_shared.plan_store.types import (
    CreatePlanResult,
    Plan,
    PlanMetadataUpdate,
    PlanQuery,
    PlanState,
)


class FakePlanStore(PlanStore):
    """In-memory fake implementation for testing.

    All state is provided via constructor. Supports filtering by state,
    labels (AND logic), and limit.
    """

    def __init__(self, plans: dict[str, Plan] | None = None) -> None:
        """Create FakePlanStore with pre-configured state.

        Args:
            plans: Mapping of plan_identifier -> Plan
        """
        self._plans = plans or {}
        self._closed_plans: list[str] = []
        self._next_id = 1
        self._current_user: str | None = "test-user"
        self._labels: dict[str, tuple[str, str]] = {}  # label -> (description, color)
        self._created_plans: list[CreatePlanResult] = []

    @property
    def closed_plans(self) -> list[str]:
        """Read-only access to closed plans for test assertions.

        Returns list of plan identifiers that were closed.
        """
        return self._closed_plans

    @property
    def created_plans(self) -> list[CreatePlanResult]:
        """Read-only access to created plans for test assertions.

        Returns list of CreatePlanResult for plans created during test.
        """
        return self._created_plans

    @property
    def labels(self) -> dict[str, tuple[str, str]]:
        """Read-only access to created labels for test assertions.

        Returns mapping of label name -> (description, color).
        """
        return self._labels

    def set_current_user(self, user: str | None) -> None:
        """Configure current user for testing.

        Args:
            user: Username to return from get_current_user(), or None
        """
        self._current_user = user

    def get_plan(self, repo_root: Path, plan_identifier: str) -> Plan:
        """Get plan from fake storage.

        Args:
            repo_root: Repository root directory (ignored in fake)
            plan_identifier: Plan identifier

        Returns:
            Plan from fake storage

        Raises:
            RuntimeError: If plan identifier not found (simulates provider error)
        """
        if plan_identifier not in self._plans:
            msg = f"Plan '{plan_identifier}' not found"
            raise RuntimeError(msg)
        return self._plans[plan_identifier]

    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        """Query plans from fake storage.

        Args:
            repo_root: Repository root directory (ignored in fake)
            query: Filter criteria (labels, state, limit)

        Returns:
            List of Plan matching the criteria
        """
        plans = list(self._plans.values())

        # Filter by state
        if query.state:
            plans = [plan for plan in plans if plan.state == query.state]

        # Filter by labels (AND logic - all must match)
        if query.labels:
            plans = [plan for plan in plans if all(label in plan.labels for label in query.labels)]

        # Apply limit
        if query.limit:
            plans = plans[: query.limit]

        return plans

    def get_provider_name(self) -> str:
        """Get the provider name.

        Returns:
            "fake"
        """
        return "fake"

    def close_plan(self, repo_root: Path, identifier: str) -> None:
        """Close a plan in fake storage.

        Args:
            repo_root: Repository root directory (ignored in fake)
            identifier: Plan identifier

        Raises:
            RuntimeError: If plan identifier not found (simulates provider error)
        """
        if identifier not in self._plans:
            msg = f"Plan '{identifier}' not found"
            raise RuntimeError(msg)

        # Update plan state to closed
        current_plan = self._plans[identifier]
        self._plans[identifier] = Plan(
            plan_identifier=current_plan.plan_identifier,
            title=current_plan.title,
            body=current_plan.body,
            state=PlanState.CLOSED,
            url=current_plan.url,
            labels=current_plan.labels,
            assignees=current_plan.assignees,
            created_at=current_plan.created_at,
            updated_at=current_plan.updated_at,
            metadata=current_plan.metadata,
        )
        self._closed_plans.append(identifier)

    # === WRITE OPERATIONS ===

    def create_plan(
        self,
        repo_root: Path,
        title: str,
        body: str,
        labels: list[str],
    ) -> CreatePlanResult:
        """Create plan in memory.

        Args:
            repo_root: Repository root directory (ignored in fake)
            title: Plan title (without [erk-plan] suffix)
            body: Plan content
            labels: Additional labels (erk-plan added automatically)

        Returns:
            CreatePlanResult with generated plan_identifier and url
        """
        plan_id = str(self._next_id)
        self._next_id += 1

        now = datetime.now(UTC)
        all_labels = ["erk-plan"] + [label for label in labels if label != "erk-plan"]

        plan = Plan(
            plan_identifier=plan_id,
            title=f"{title} [erk-plan]",
            body=body,
            state=PlanState.OPEN,
            url=f"https://github.com/test/repo/issues/{plan_id}",
            labels=all_labels,
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={"number": int(plan_id)},
        )

        self._plans[plan_id] = plan
        result = CreatePlanResult(plan_identifier=plan_id, url=plan.url)
        self._created_plans.append(result)
        return result

    def update_plan_metadata(
        self,
        repo_root: Path,
        plan_identifier: str,
        updates: PlanMetadataUpdate,
    ) -> None:
        """Update plan metadata in memory.

        Args:
            repo_root: Repository root directory (ignored in fake)
            plan_identifier: Plan identifier
            updates: Metadata fields to update

        Raises:
            RuntimeError: If plan not found
        """
        if plan_identifier not in self._plans:
            msg = f"Plan '{plan_identifier}' not found"
            raise RuntimeError(msg)

        current = self._plans[plan_identifier]
        new_metadata = dict(current.metadata)

        if updates.worktree_name is not None:
            new_metadata["worktree_name"] = updates.worktree_name
        if updates.last_dispatched_run_id is not None:
            new_metadata["last_dispatched_run_id"] = updates.last_dispatched_run_id
        if updates.last_dispatched_at is not None:
            new_metadata["last_dispatched_at"] = updates.last_dispatched_at
        if updates.last_local_impl_at is not None:
            new_metadata["last_local_impl_at"] = updates.last_local_impl_at
        if updates.last_remote_impl_at is not None:
            new_metadata["last_remote_impl_at"] = updates.last_remote_impl_at

        self._plans[plan_identifier] = Plan(
            plan_identifier=current.plan_identifier,
            title=current.title,
            body=current.body,
            state=current.state,
            url=current.url,
            labels=current.labels,
            assignees=current.assignees,
            created_at=current.created_at,
            updated_at=datetime.now(UTC),
            metadata=new_metadata,
        )

    def ensure_label(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Track label in memory.

        Args:
            repo_root: Repository root directory (ignored in fake)
            label: Label name
            description: Label description
            color: Label color (6-char hex, no #)
        """
        self._labels[label] = (description, color)

    def get_current_user(self) -> str | None:
        """Return configured test user.

        Returns:
            Username configured via set_current_user(), default "test-user"
        """
        return self._current_user
