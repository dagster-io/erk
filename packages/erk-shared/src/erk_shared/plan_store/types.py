"""Core types for provider-agnostic plan storage."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PlanState(Enum):
    """State of a plan."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


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
        objective_issue: Parent objective issue number, or None if not linked
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
    objective_issue: int | None


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


@dataclass(frozen=True)
class CreatePlanResult:
    """Result of creating a plan.

    Fields:
        plan_id: Provider-specific plan identifier as string
        url: Web URL to view the created plan
    """

    plan_id: str
    url: str
