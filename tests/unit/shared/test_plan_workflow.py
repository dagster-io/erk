"""Unit tests for shared plan workflow helpers.

Tests the shared logic for preparing plans for worktree creation.
"""

from datetime import datetime

from erk_shared.plan_store.types import Plan, PlanState
from erk_shared.plan_workflow import (
    PlanBranchSetup,
    PlanValidationFailed,
    prepare_plan_for_worktree,
)


def _make_plan(
    *,
    pr_identifier: str = "123",
    title: str = "[erk-pr] Test Issue",
    body: str = "Plan content",
    state: PlanState = PlanState.OPEN,
    url: str = "https://github.com/org/repo/issues/123",
    labels: list[str] | None = None,
    header_fields: dict[str, object] | None = None,
) -> Plan:
    """Create a minimal Plan for testing."""
    return Plan(
        pr_identifier=pr_identifier,
        title=title,
        body=body,
        state=state,
        url=url,
        labels=labels if labels is not None else ["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        metadata={},
        objective_id=None,
        header_fields=header_fields
        if header_fields is not None
        else {"branch_name": "plan-test-issue-01-01-0000"},
    )


def test_prepare_plan_valid_returns_setup() -> None:
    """Valid plan with [erk-pr] title prefix returns PlanBranchSetup."""
    plan = _make_plan(
        labels=["erk-pr", "enhancement"],
        header_fields={"branch_name": "plan-test-01-15-1430"},
    )
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanBranchSetup)
    assert result.warnings == ()


def test_prepare_plan_missing_title_prefix_returns_failure() -> None:
    """Plan without [erk-pr] title prefix returns PlanValidationFailed."""
    plan = _make_plan(title="No prefix plan")
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanValidationFailed)
    assert "'[erk-pr]' title prefix" in result.message


def test_prepare_plan_non_open_generates_warning() -> None:
    """Non-OPEN plan generates warning in result."""
    plan = _make_plan(
        state=PlanState.CLOSED,
        labels=["erk-pr"],
        header_fields={"branch_name": "plan-test-01-15-1430"},
    )
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanBranchSetup)
    assert len(result.warnings) == 1
    assert "is CLOSED" in result.warnings[0]
    assert "Proceeding anyway" in result.warnings[0]


def test_prepare_plan_converts_identifier_to_int() -> None:
    """Plan identifier string is converted to pr number int."""
    plan = _make_plan(
        pr_identifier="789",
        header_fields={"branch_name": "plan-test-01-01-0000"},
    )
    timestamp = datetime(2024, 1, 1, 0, 0)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanBranchSetup)
    assert result.plan_number == 789
    assert isinstance(result.plan_number, int)


def test_prepare_plan_invalid_identifier_returns_failure() -> None:
    """Non-numeric plan identifier returns PlanValidationFailed."""
    plan = _make_plan(pr_identifier="not-a-number")
    timestamp = datetime(2024, 1, 1, 0, 0)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanValidationFailed)
    assert "not a valid plan number" in result.message
    assert "not-a-number" in result.message


def test_prepare_plan_with_objective_id_populates_objective_issue() -> None:
    """Plan with objective_id populates PlanBranchSetup.objective_issue field."""
    plan = Plan(
        pr_identifier="123",
        title="[erk-pr] Test Issue",
        body="Plan content",
        state=PlanState.OPEN,
        url="https://github.com/org/repo/issues/123",
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        metadata={},
        objective_id=456,
        header_fields={"branch_name": "plan-test-01-15-1430"},
    )
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanBranchSetup)
    assert result.objective_issue == 456


def test_prepare_plan_without_objective_id_has_none() -> None:
    """Plan without objective_id results in objective_issue=None."""
    plan = _make_plan()
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanBranchSetup)
    assert result.objective_issue is None


def test_uses_existing_branch_from_header() -> None:
    """Plan with branch_name in header_fields uses it directly."""
    plan = _make_plan(
        pr_identifier="456",
        title="[erk-pr] Add New Feature",
        header_fields={"branch_name": "plan-add-new-feature-01-15-1430"},
    )
    timestamp = datetime(2024, 3, 10, 9, 15)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanBranchSetup)
    assert result.branch_name == "plan-add-new-feature-01-15-1430"
    assert result.plan_number == 456


def test_missing_branch_returns_failure() -> None:
    """Plan without branch_name in header_fields returns failure."""
    plan = _make_plan(
        pr_identifier="456",
        title="[erk-pr] Add New Feature",
        header_fields={},
    )
    timestamp = datetime(2024, 3, 10, 9, 15)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanValidationFailed)
    assert "missing required branch_name" in result.message


def test_empty_branch_returns_failure() -> None:
    """Plan with empty branch_name in header_fields returns failure."""
    plan = _make_plan(
        pr_identifier="456",
        title="[erk-pr] Add New Feature",
        header_fields={"branch_name": ""},
    )
    timestamp = datetime(2024, 3, 10, 9, 15)

    result = prepare_plan_for_worktree(plan, timestamp, warn_non_open=True)

    assert isinstance(result, PlanValidationFailed)
    assert "missing required branch_name" in result.message
