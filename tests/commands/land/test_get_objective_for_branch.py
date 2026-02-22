"""Tests for get_objective_for_branch helper in erk land command.

Tests the branch-name fallback behavior: when the plan backend returns
a plan with objective_id=None (e.g., because the PR body lost the
plan-header block during implementation), the function falls back to
parsing the objective number from the branch name.
"""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.objective_helpers import get_objective_for_branch
from erk.core.context import context_for_test
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _create_plan_issue(
    number: int,
    *,
    objective_issue: int | None,
) -> IssueInfo:
    """Create a plan issue with optional objective in plan-header metadata."""
    body = format_plan_header_body_for_test(objective_issue=objective_issue)
    return IssueInfo(
        number=number,
        title=f"P{number}: Test Plan",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author="testuser",
    )


def _create_plan_issue_without_header(number: int) -> IssueInfo:
    """Create a plan issue with no plan-header block (simulates overwritten body)."""
    return IssueInfo(
        number=number,
        title=f"P{number}: Test Plan",
        body="## Summary\n\nImplementation PR body without plan-header block.",
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author="testuser",
    )


def test_returns_objective_from_plan_metadata(tmp_path: Path) -> None:
    """Plan has objective_id in metadata — return it directly."""
    issue = _create_plan_issue(42, objective_issue=100)
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "P42-O100-test-feature-01-15-1430")

    assert result == 100


def test_falls_back_to_branch_name_when_objective_id_none(tmp_path: Path) -> None:
    """Plan exists but objective_id is None — fall back to branch name parsing."""
    issue = _create_plan_issue_without_header(42)
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "P42-O7709-plan-lazy-tip-sync-f-02-21-1116")

    assert result == 7709


def test_falls_back_to_branch_name_when_plan_not_found(tmp_path: Path) -> None:
    """No plan found for branch — fall back to branch name parsing."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "P42-O456-fix-auth-bug-01-15-1430")

    assert result == 456


def test_returns_none_when_no_objective_anywhere(tmp_path: Path) -> None:
    """No plan found and branch has no objective number — return None."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "feature-branch")

    assert result is None


def test_falls_back_to_legacy_plan_prefix(tmp_path: Path) -> None:
    """Branch with legacy plan/ prefix and no plan found — extract from name."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "plan/O7709-plan-lazy-tip-sync-f-02-21-1116")

    assert result == 7709


def test_falls_back_to_plnd_prefix(tmp_path: Path) -> None:
    """Branch with plnd/ prefix and no plan found — extract from name."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    result = get_objective_for_branch(ctx, tmp_path, "plnd/O456-fix-auth-01-15-1430")

    assert result == 456


def test_prefers_plan_metadata_over_branch_name(tmp_path: Path) -> None:
    """Plan has objective_id in metadata — prefer it over branch name."""
    issue = _create_plan_issue(42, objective_issue=100)
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    ctx = context_for_test(issues=issues_ops, cwd=tmp_path)

    # Branch encodes O999, but plan metadata says 100 — metadata wins
    result = get_objective_for_branch(ctx, tmp_path, "P42-O999-test-feature-01-15-1430")

    assert result == 100
