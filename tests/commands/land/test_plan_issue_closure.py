"""Tests for plan issue closure display in erk land command.

Tests the check_and_display_plan_issue_closure helper that shows:
- Confirmation when plan issue is closed after landing
- Warning when plan issue is unexpectedly still open
- No output when branch has no plan issue prefix
"""

from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from erk.cli.commands.objective_helpers import check_and_display_plan_issue_closure
from erk.core.context import context_for_test
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo


def _create_issue(number: int, state: str) -> IssueInfo:
    """Create a test issue with the given state."""
    return IssueInfo(
        number=number,
        title=f"P{number}: Test Plan",
        body="Test body",
        state=state,
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author="testuser",
    )


def test_displays_closed_confirmation_when_issue_closed(tmp_path: Path) -> None:
    """Test that closed plan issue shows green checkmark confirmation."""
    issue = _create_issue(42, "CLOSED")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
    )

    # Capture stderr output (user_output goes to stderr)
    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
        )

    assert result == 42
    output = captured.getvalue()
    assert "Closed plan issue #42" in output


def test_displays_warning_when_issue_still_open(tmp_path: Path) -> None:
    """Test that open plan issue shows warning about expected auto-close."""
    issue = _create_issue(42, "OPEN")
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
        )

    assert result == 42
    output = captured.getvalue()
    assert "Plan issue #42 still open" in output
    assert "expected auto-close" in output


def test_returns_none_for_non_plan_branch(tmp_path: Path) -> None:
    """Test that branches without P<num>- prefix return None with no output."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "feature-branch",
        )

    assert result is None
    assert captured.getvalue() == ""


def test_returns_none_when_issue_not_found(tmp_path: Path) -> None:
    """Test that missing issue returns None with no output."""
    # No issues exist
    issues_ops = FakeGitHubIssues(username="testuser", issues={})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P42-test-feature",
        )

    assert result is None
    assert captured.getvalue() == ""


def test_handles_branch_with_complex_prefix(tmp_path: Path) -> None:
    """Test that complex branch names with P<num>- are handled correctly."""
    issue = _create_issue(1234, "CLOSED")
    issues_ops = FakeGitHubIssues(username="testuser", issues={1234: issue})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(
            ctx,
            tmp_path,
            "P1234-add-feature-with-long-name-01-05-1430",
        )

    assert result == 1234
    output = captured.getvalue()
    assert "Closed plan issue #1234" in output
