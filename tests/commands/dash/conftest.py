"""Shared fixtures and helpers for dash command tests."""

from datetime import UTC, datetime

from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.plan_helpers import make_test_plan, plan_to_issue

__all__ = ["make_plan", "plan_to_issue"]


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
    """Create a Plan with common defaults for testing.

    Wrapper around make_test_plan for backward compatibility with existing code
    that uses the dash-specific parameter names (day instead of timestamps).
    """
    return make_test_plan(
        plan_identifier,
        title=title,
        body=body,
        state=state,
        labels=labels,
        created_at=datetime(2024, 1, day, tzinfo=UTC),
        updated_at=datetime(2024, 1, day, tzinfo=UTC),
        metadata={"number": int(plan_identifier)},
        objective_issue=objective_issue,
    )
