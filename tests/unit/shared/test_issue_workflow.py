"""Unit tests for shared plan workflow helpers.

Tests the shared logic for preparing plans for worktree creation.
"""

from datetime import UTC, datetime

from tests.test_utils.plan_helpers import make_test_plan

from erk_shared.issue_workflow import (
    IssueBranchSetup,
    IssueValidationFailed,
    prepare_plan_for_worktree,
)
from erk_shared.plan_store.types import Plan, PlanState

# Tests for prepare_plan_for_worktree


def test_prepare_plan_valid_returns_setup() -> None:
    """Valid plan with erk-plan label returns IssueBranchSetup."""
    plan = make_test_plan(123, labels=["erk-plan", "enhancement"])
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.warnings == ()


def test_prepare_plan_missing_label_returns_failure() -> None:
    """Plan without erk-plan label returns IssueValidationFailed."""
    plan = make_test_plan(123, labels=["bug", "enhancement"])
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueValidationFailed)
    assert "must have 'erk-plan' label" in result.message


def test_prepare_plan_non_open_generates_warning() -> None:
    """Non-OPEN plan generates warning in result."""
    plan = make_test_plan(123, state=PlanState.CLOSED)
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert len(result.warnings) == 1
    assert "is CLOSED" in result.warnings[0]
    assert "Proceeding anyway" in result.warnings[0]


def test_prepare_plan_generates_branch_name() -> None:
    """Branch name is generated from plan metadata."""
    plan = make_test_plan(456, title="Add New Feature")
    timestamp = datetime(2024, 3, 10, 9, 15)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.branch_name == "P456-add-new-feature-03-10-0915"
    assert result.issue_number == 456
    assert result.issue_title == "Add New Feature"


def test_prepare_plan_converts_identifier_to_int() -> None:
    """Plan identifier string is converted to issue number int."""
    plan = make_test_plan(789)
    timestamp = datetime(2024, 1, 1, 0, 0)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.issue_number == 789
    assert isinstance(result.issue_number, int)


def test_prepare_plan_invalid_identifier_returns_failure() -> None:
    """Non-numeric plan identifier returns IssueValidationFailed.

    Note: This test uses direct Plan() construction to test invalid identifier
    handling - a scenario that make_test_plan() intentionally doesn't support.
    """
    # Create plan with invalid identifier directly (make_test_plan doesn't support this)
    plan = Plan(
        plan_identifier="not-a-number",
        title="Test Plan",
        body="",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/0",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    timestamp = datetime(2024, 1, 1, 0, 0)

    result = prepare_plan_for_worktree(plan, timestamp)

    assert isinstance(result, IssueValidationFailed)
    assert "not a valid issue number" in result.message
    assert "not-a-number" in result.message
