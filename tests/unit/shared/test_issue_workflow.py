"""Unit tests for shared issue workflow helpers.

Tests the shared logic for preparing GitHub issues for worktree creation.
"""

from datetime import datetime

from erk_shared.github.issues import IssueInfo
from erk_shared.issue_workflow import (
    IssueBranchSetup,
    IssueValidationFailed,
    prepare_issue_for_worktree,
    prepare_plan_for_worktree,
)
from erk_shared.plan_store.types import Plan, PlanState


def _make_issue_info(
    number: int = 123,
    title: str = "Test Issue",
    body: str = "Plan content",
    state: str = "OPEN",
    url: str = "https://github.com/org/repo/issues/123",
    labels: list[str] | None = None,
) -> IssueInfo:
    """Create a minimal IssueInfo for testing."""
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=url,
        labels=labels if labels is not None else ["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
        author="testuser",
    )


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
    )


# Tests for prepare_issue_for_worktree


def test_prepare_issue_valid_returns_setup() -> None:
    """Valid issue with erk-plan label returns IssueBranchSetup."""
    issue = _make_issue_info(labels=["erk-plan", "enhancement"])
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_issue_for_worktree(issue, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.warnings == ()


def test_prepare_issue_missing_label_returns_failure() -> None:
    """Issue without erk-plan label returns IssueValidationFailed."""
    issue = _make_issue_info(labels=["bug", "enhancement"])
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_issue_for_worktree(issue, timestamp)

    assert isinstance(result, IssueValidationFailed)
    assert "must have 'erk-plan' label" in result.message
    assert "gh issue edit 123 --add-label erk-plan" in result.message


def test_prepare_issue_non_open_generates_warning() -> None:
    """Non-OPEN issue generates warning in result."""
    issue = _make_issue_info(state="CLOSED", labels=["erk-plan"])
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_issue_for_worktree(issue, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert len(result.warnings) == 1
    assert "is CLOSED" in result.warnings[0]
    assert "Proceeding anyway" in result.warnings[0]


def test_prepare_issue_non_open_warning_can_be_disabled() -> None:
    """warn_non_open=False suppresses warning."""
    issue = _make_issue_info(state="CLOSED", labels=["erk-plan"])
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_issue_for_worktree(issue, timestamp, warn_non_open=False)

    assert isinstance(result, IssueBranchSetup)
    assert result.warnings == ()


def test_prepare_issue_generates_branch_name_with_correct_format() -> None:
    """Branch name follows P{num}-{slug}-{timestamp} format."""
    issue = _make_issue_info(number=123, title="Fix Auth Bug")
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_issue_for_worktree(issue, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.branch_name == "P123-fix-auth-bug-01-15-1430"


def test_prepare_issue_long_title_is_truncated() -> None:
    """Long titles are truncated before timestamp."""
    issue = _make_issue_info(
        number=123, title="This is a very long title that should be truncated"
    )
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_issue_for_worktree(issue, timestamp)

    assert isinstance(result, IssueBranchSetup)
    # Base (P123-this-is...) truncated to 31 chars, then timestamp appended
    assert len(result.branch_name) <= 31 + 11  # 31 + "-01-15-1430"
    assert result.branch_name.startswith("P123-")
    assert result.branch_name.endswith("-01-15-1430")


def test_prepare_issue_returns_all_issue_metadata() -> None:
    """Result includes all issue metadata."""
    issue = _make_issue_info(
        number=42,
        title="My Feature",
        body="Implementation details here",
        url="https://github.com/org/repo/issues/42",
    )
    timestamp = datetime(2024, 6, 20, 10, 0)

    result = prepare_issue_for_worktree(issue, timestamp)

    assert isinstance(result, IssueBranchSetup)
    assert result.issue_number == 42
    assert result.issue_title == "My Feature"
    assert result.issue_url == "https://github.com/org/repo/issues/42"
    assert result.plan_content == "Implementation details here"


def test_prepare_issue_worktree_name_is_sanitized_branch_name() -> None:
    """Worktree name is the sanitized version of branch name."""
    issue = _make_issue_info(number=123, title="Fix Bug")
    timestamp = datetime(2024, 1, 15, 14, 30)

    result = prepare_issue_for_worktree(issue, timestamp)

    assert isinstance(result, IssueBranchSetup)
    # Worktree name should be sanitized (lowercased, safe chars)
    assert result.worktree_name == result.branch_name


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
