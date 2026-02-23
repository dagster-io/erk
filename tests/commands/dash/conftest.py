"""Shared fixtures and helpers for dash command tests."""

from datetime import UTC, datetime

import pytest

from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.plan_store.types import Plan, PlanState


@pytest.fixture(autouse=True)
def _force_github_plan_backend() -> None:
    """Force github plan backend for all dash tests.

    These tests use issue-based plan data (Plan objects with plan_identifier
    as issue numbers). The github backend ensures the correct column layout
    with a separate PR column and plan-first table structure.
    """
    import os

    original = os.environ.get("ERK_PLAN_BACKEND")
    os.environ["ERK_PLAN_BACKEND"] = "github"
    yield  # type: ignore[misc]
    if original is None:
        os.environ.pop("ERK_PLAN_BACKEND", None)
    else:
        os.environ["ERK_PLAN_BACKEND"] = original


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
