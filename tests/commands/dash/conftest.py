"""Shared fixtures and helpers for dash command tests."""

from datetime import UTC, datetime

from erk_shared.github.issues.types import IssueInfo
from erk_shared.plan_store.types import Plan, PlanState


def plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup."""
    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        author="test-user",
    )


def make_plan(
    plan_identifier: str,
    title: str,
    state: PlanState,
    labels: list[str],
    body: str,
    day: int,
    *,
    objective_issue: int | None = None,
) -> Plan:
    """Create a Plan with common defaults for testing."""
    return Plan(
        plan_identifier=plan_identifier,
        title=title,
        body=body,
        state=state,
        url=f"https://github.com/owner/repo/issues/{plan_identifier}",
        labels=labels,
        assignees=[],
        created_at=datetime(2024, 1, day, tzinfo=UTC),
        updated_at=datetime(2024, 1, day, tzinfo=UTC),
        metadata={"number": int(plan_identifier)},
        objective_id=objective_issue,
    )
