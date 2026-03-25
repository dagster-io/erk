"""Tests for get_objective_for_branch helper in erk land command.

Tests the branch-name extraction behavior: since resolve_plan_id_for_branch
always returns None (plan IDs are not encoded in branch names), the function
relies solely on extract_objective_number() which parses plnd/O{N}-... patterns.
"""

from pathlib import Path

from erk.cli.commands.objective_helpers import get_objective_for_branch
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.test_utils.test_context import context_for_test


def test_extracts_objective_from_plnd_branch(tmp_path: Path) -> None:
    """plnd/ branch with O-prefix — extract objective from branch name."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "plnd/O100-test-feature-01-15-1430")

    assert result == 100


def test_extracts_objective_from_plnd_branch_large_number(tmp_path: Path) -> None:
    """plnd/ branch with large objective number."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "plnd/O7709-plan-lazy-tip-sync-f-02-21-1116")

    assert result == 7709


def test_returns_none_for_plnd_branch_without_objective(tmp_path: Path) -> None:
    """plnd/ branch without O-prefix — no objective number, return None."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "plnd/fix-auth-bug-01-15-1430")

    assert result is None


def test_returns_none_when_no_objective_anywhere(tmp_path: Path) -> None:
    """No plan found and branch has no objective number — return None."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "feature-branch")

    assert result is None


def test_falls_back_to_legacy_plan_prefix(tmp_path: Path) -> None:
    """Branch with legacy plan/ prefix — extract from name."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "plan/O7709-plan-lazy-tip-sync-f-02-21-1116")

    assert result == 7709


def test_extracts_from_plnd_prefix(tmp_path: Path) -> None:
    """Branch with plnd/ prefix — extract from name."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "plnd/O456-fix-auth-01-15-1430")

    assert result == 456


def test_p_prefix_branch_returns_none(tmp_path: Path) -> None:
    """P-prefix branches no longer resolve plan IDs — objective extraction returns None."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    # P42-O999 was the old format — extract_objective_number no longer matches this
    result = get_objective_for_branch(ctx, tmp_path, "P42-O999-test-feature-01-15-1430")

    assert result is None
