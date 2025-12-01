"""Core types for provider-agnostic plan storage."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PlanState(Enum):
    """State of a plan."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class CreatePlanResult:
    """Result from creating a plan.

    Attributes:
        plan_identifier: Provider-specific ID (e.g., "42" for GitHub issue number)
        url: Web URL to view the plan
    """

    plan_identifier: str
    url: str


@dataclass(frozen=True)
class PlanMetadataUpdate:
    """Mutable metadata fields that can be updated.

    All fields are optional - only provided fields are updated.
    Used for updating worktree_name, last_dispatched_run_id, etc.
    Does NOT update plan content or title.

    Attributes:
        worktree_name: Name of worktree implementing this plan
        last_dispatched_run_id: ID of most recent workflow dispatch
        last_dispatched_at: ISO timestamp of most recent dispatch
        last_local_impl_at: ISO timestamp of most recent local implementation
        last_remote_impl_at: ISO timestamp of most recent remote implementation
    """

    worktree_name: str | None = None
    last_dispatched_run_id: str | None = None
    last_dispatched_at: str | None = None
    last_local_impl_at: str | None = None
    last_remote_impl_at: str | None = None


@dataclass(frozen=True)
class Plan:
    """Provider-agnostic representation of a plan.

    Fields:
        plan_identifier: Provider-specific ID as string
            (GitHub: "42", Jira: "PROJ-123", Linear: UUID)
        title: Plan title
        body: Plan body/description
        state: Plan state (OPEN or CLOSED)
        url: Web URL to view the plan
        labels: List of label names
        assignees: List of assignee usernames
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Provider-specific fields (e.g., {"number": 42} for GitHub)
    """

    plan_identifier: str
    title: str
    body: str
    state: PlanState
    url: str
    labels: list[str]
    assignees: list[str]
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, object]


@dataclass(frozen=True)
class PlanQuery:
    """Query parameters for filtering plans.

    Fields:
        labels: Filter by labels (all must match - AND logic)
        state: Filter by state (OPEN, CLOSED, or None for all)
        limit: Maximum number of results to return
    """

    labels: list[str] | None = None
    state: PlanState | None = None
    limit: int | None = None
