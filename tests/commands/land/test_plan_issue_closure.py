"""Tests for plan issue closure display in erk land command.

Since resolve_plan_id_for_branch always returns None (plan IDs are not
encoded in branch names), check_and_display_plan_issue_closure always
returns None for any branch. These tests verify that behavior.
"""

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from erk.cli.commands.objective_helpers import check_and_display_plan_issue_closure
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.test_utils.test_context import context_for_test


def test_returns_none_for_plnd_branch(tmp_path: Path) -> None:
    """plnd/ branches don't encode plan IDs — returns None with no output."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(ctx, tmp_path, "plnd/test-feature-01-15-1430")

    assert result is None
    assert captured.getvalue() == ""


def test_returns_none_for_feature_branch(tmp_path: Path) -> None:
    """Non-plan branches return None with no output."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(ctx, tmp_path, "feature-branch")

    assert result is None
    assert captured.getvalue() == ""


def test_returns_none_for_p_prefix_branch(tmp_path: Path) -> None:
    """Legacy P-prefix branches no longer resolve plan IDs — returns None."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    captured = StringIO()
    with patch("sys.stderr", captured):
        result = check_and_display_plan_issue_closure(ctx, tmp_path, "P42-test-feature")

    assert result is None
    assert captured.getvalue() == ""
