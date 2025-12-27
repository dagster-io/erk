"""Unit tests for shared issue workflow helpers.

Tests the shared logic for preparing GitHub issues for worktree creation.
"""

from datetime import datetime

import pytest

from erk_shared.github.issues import IssueInfo
from erk_shared.issue_workflow import (
    IssueBranchSetup,
    IssueValidationError,
    prepare_issue_for_worktree,
    prepare_plan_for_worktree,
    validate_issue_for_worktree,
    validate_plan_for_worktree,
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


class TestValidateIssueForWorktree:
    """Tests for validate_issue_for_worktree()."""

    def test_valid_issue_with_erk_plan_label(self) -> None:
        """Valid issue with erk-plan label returns no warnings."""
        issue = _make_issue_info(labels=["erk-plan", "enhancement"])
        warnings = validate_issue_for_worktree(issue)
        assert warnings == []

    def test_missing_erk_plan_label_raises_error(self) -> None:
        """Issue without erk-plan label raises IssueValidationError."""
        issue = _make_issue_info(labels=["bug", "enhancement"])

        with pytest.raises(IssueValidationError) as exc_info:
            validate_issue_for_worktree(issue)

        assert "must have 'erk-plan' label" in str(exc_info.value)
        assert "gh issue edit 123 --add-label erk-plan" in str(exc_info.value)

    def test_non_open_issue_generates_warning(self) -> None:
        """Non-OPEN issue generates warning."""
        issue = _make_issue_info(state="CLOSED", labels=["erk-plan"])
        warnings = validate_issue_for_worktree(issue)
        assert len(warnings) == 1
        assert "is CLOSED" in warnings[0]
        assert "Proceeding anyway" in warnings[0]

    def test_non_open_warning_can_be_disabled(self) -> None:
        """warn_non_open=False suppresses warning."""
        issue = _make_issue_info(state="CLOSED", labels=["erk-plan"])
        warnings = validate_issue_for_worktree(issue, warn_non_open=False)
        assert warnings == []


class TestValidatePlanForWorktree:
    """Tests for validate_plan_for_worktree()."""

    def test_valid_plan_with_erk_plan_label(self) -> None:
        """Valid plan with erk-plan label returns no warnings."""
        plan = _make_plan(labels=["erk-plan", "enhancement"])
        warnings = validate_plan_for_worktree(plan)
        assert warnings == []

    def test_missing_erk_plan_label_raises_error(self) -> None:
        """Plan without erk-plan label raises IssueValidationError."""
        plan = _make_plan(labels=["bug", "enhancement"])

        with pytest.raises(IssueValidationError) as exc_info:
            validate_plan_for_worktree(plan)

        assert "must have 'erk-plan' label" in str(exc_info.value)

    def test_non_open_plan_generates_warning(self) -> None:
        """Non-OPEN plan generates warning."""
        plan = _make_plan(state=PlanState.CLOSED, labels=["erk-plan"])
        warnings = validate_plan_for_worktree(plan)
        assert len(warnings) == 1
        assert "is CLOSED" in warnings[0]
        assert "Proceeding anyway" in warnings[0]


class TestPrepareIssueForWorktree:
    """Tests for prepare_issue_for_worktree()."""

    def test_generates_branch_name_with_correct_format(self) -> None:
        """Branch name follows P{num}-{slug}-{timestamp} format."""
        issue = _make_issue_info(number=123, title="Fix Auth Bug")
        timestamp = datetime(2024, 1, 15, 14, 30)

        result = prepare_issue_for_worktree(issue, timestamp)

        assert result.branch_name == "P123-fix-auth-bug-01-15-1430"

    def test_long_title_is_truncated(self) -> None:
        """Long titles are truncated before timestamp."""
        issue = _make_issue_info(
            number=123, title="This is a very long title that should be truncated"
        )
        timestamp = datetime(2024, 1, 15, 14, 30)

        result = prepare_issue_for_worktree(issue, timestamp)

        # Base (P123-this-is...) truncated to 31 chars, then timestamp appended
        assert len(result.branch_name) <= 31 + 11  # 31 + "-01-15-1430"
        assert result.branch_name.startswith("P123-")
        assert result.branch_name.endswith("-01-15-1430")

    def test_returns_all_issue_metadata(self) -> None:
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

    def test_worktree_name_is_sanitized_branch_name(self) -> None:
        """Worktree name is the sanitized version of branch name."""
        issue = _make_issue_info(number=123, title="Fix Bug")
        timestamp = datetime(2024, 1, 15, 14, 30)

        result = prepare_issue_for_worktree(issue, timestamp)

        # Worktree name should be sanitized (lowercased, safe chars)
        assert result.worktree_name == result.branch_name


class TestPreparePlanForWorktree:
    """Tests for prepare_plan_for_worktree()."""

    def test_generates_branch_name_from_plan(self) -> None:
        """Branch name is generated from plan metadata."""
        plan = _make_plan(plan_identifier="456", title="Add New Feature")
        timestamp = datetime(2024, 3, 10, 9, 15)

        result = prepare_plan_for_worktree(plan, timestamp)

        assert result.branch_name == "P456-add-new-feature-03-10-0915"
        assert result.issue_number == 456
        assert result.issue_title == "Add New Feature"

    def test_converts_plan_identifier_to_int(self) -> None:
        """Plan identifier string is converted to issue number int."""
        plan = _make_plan(plan_identifier="789")
        timestamp = datetime(2024, 1, 1, 0, 0)

        result = prepare_plan_for_worktree(plan, timestamp)

        assert result.issue_number == 789
        assert isinstance(result.issue_number, int)
