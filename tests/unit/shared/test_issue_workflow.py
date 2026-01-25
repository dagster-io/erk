"""Unit tests for shared plan workflow helpers.

Tests the shared logic for preparing plans for worktree creation.
"""

from datetime import datetime

from erk_shared.issue_workflow import (
    IssueBranchSetup,
    IssueValidationFailed,
    prepare_plan_for_worktree,
)
from erk_shared.plan_store.types import Plan, PlanState


def _make_plan(
    plan_identifier: str = "123",
    title: str = "Test Issue",
    body: str = "Plan content",
    state: PlanState = PlanState.OPEN,
    url: str = "https://github.com/org/repo/issues/123",
    labels: list[str] | None = None,
) -> Plan:
    """Create a minimal Plan for testing."""
    return Plan(
        plan_identifier=plan_identifier,
        title=title,
        body=body,
        state=state,
        url=url,
        labels=labels if labels is not None else ["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        metadata={},
        objective_id=None,
    )


# Tests for prepare_plan_for_worktree


def test_prepare_plan_valid_returns_setup() -> None:
    """Valid plan with erk-plan label returns IssueBranchSetup."""
    plan = _make_plan(labels=["erk-plan", "enhancement"])
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.warnings == ()


def test_prepare_plan_missing_label_returns_failure() -> None:
    """Plan without erk-plan label returns IssueValidationFailed."""
    plan = _make_plan(labels=["bug", "enhancement"])
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueValidationFailed)
    assert "must have 'erk-plan' label" in result.message


def test_prepare_plan_non_open_generates_warning() -> None:
    """Non-OPEN plan generates warning in result."""
    plan = _make_plan(state=PlanState.CLOSED, labels=["erk-plan"])
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert len(result.warnings) == 1
    assert "is CLOSED" in result.warnings[0]
    assert "Proceeding anyway" in result.warnings[0]


def test_prepare_plan_generates_branch_name() -> None:
    """Branch name is generated from plan metadata."""
    plan = _make_plan(plan_identifier="456", title="Add New Feature")
    timestamp = datetime(2024, 3, 10, 9, 15)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.branch_name == "P456-add-new-feature-03-10-0915"
    assert result.issue_number == 456
    assert result.issue_title == "Add New Feature"


def test_prepare_plan_converts_identifier_to_int() -> None:
    """Plan identifier string is converted to issue number int."""
    plan = _make_plan(plan_identifier="789")
    timestamp = datetime(2024, 1, 1, 0, 0)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.issue_number == 789
    assert isinstance(result.issue_number, int)


def test_prepare_plan_invalid_identifier_returns_failure() -> None:
    """Non-numeric plan identifier returns IssueValidationFailed."""
    plan = _make_plan(plan_identifier="not-a-number")
    timestamp = datetime(2024, 1, 1, 0, 0)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueValidationFailed)
    assert "not a valid issue number" in result.message
    assert "not-a-number" in result.message


def test_prepare_plan_with_objective_id_populates_objective_issue() -> None:
    """Plan with objective_id populates IssueBranchSetup.objective_issue."""
    plan = Plan(
        plan_identifier="123",
        title="Test Issue",
        body="Plan content",
        state=PlanState.OPEN,
        url="https://github.com/org/repo/issues/123",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        metadata={},
        objective_id=456,
    )
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.objective_issue == 456


def test_prepare_plan_without_objective_id_has_none() -> None:
    """Plan without objective_id results in objective_issue=None."""
    plan = _make_plan()
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.objective_issue is None
