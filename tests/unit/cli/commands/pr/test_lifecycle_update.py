"""Unit tests for maybe_advance_lifecycle_to_impl shared helper."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.pr.shared import maybe_advance_lifecycle_to_impl
from erk.core.context import context_for_test
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_issue(*, number: int, lifecycle_stage: str | None = None) -> IssueInfo:
    """Create a plan issue with a plan-header metadata block."""
    body = format_plan_header_body_for_test(lifecycle_stage=lifecycle_stage)
    return IssueInfo(
        number=number,
        title=f"Plan #{number}",
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        author="test-user",
    )


def test_advances_planned_to_impl(tmp_path: Path) -> None:
    """Plan at 'planned' stage gets updated to 'impl'."""
    issue = _make_issue(number=100, lifecycle_stage="planned")
    fake_issues = FakeGitHubIssues(issues={100: issue})
    ctx = context_for_test(cwd=tmp_path, issues=fake_issues)

    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="100", quiet=False)

    # Verify metadata was updated
    assert len(fake_issues.updated_bodies) == 1
    updated_body = fake_issues.updated_bodies[0][1]
    assert "lifecycle_stage: impl" in updated_body


def test_advances_none_stage_to_impl(tmp_path: Path) -> None:
    """Plan with None stage gets updated to 'impl'."""
    issue = _make_issue(number=100, lifecycle_stage=None)
    fake_issues = FakeGitHubIssues(issues={100: issue})
    ctx = context_for_test(cwd=tmp_path, issues=fake_issues)

    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="100", quiet=False)

    assert len(fake_issues.updated_bodies) == 1
    updated_body = fake_issues.updated_bodies[0][1]
    assert "lifecycle_stage: impl" in updated_body


def test_skips_when_already_impl(tmp_path: Path) -> None:
    """Plan already at 'impl' is not updated (idempotent)."""
    issue = _make_issue(number=100, lifecycle_stage="impl")
    fake_issues = FakeGitHubIssues(issues={100: issue})
    ctx = context_for_test(cwd=tmp_path, issues=fake_issues)

    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="100", quiet=False)

    # No body update should have been made
    assert len(fake_issues.updated_bodies) == 0


def test_skips_when_plan_not_found(tmp_path: Path) -> None:
    """PlanNotFound result causes graceful return."""
    fake_issues = FakeGitHubIssues()  # No issues
    ctx = context_for_test(cwd=tmp_path, issues=fake_issues)

    # Should not raise
    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="999", quiet=False)

    assert len(fake_issues.updated_bodies) == 0


def test_advances_planning_stage_to_impl(tmp_path: Path) -> None:
    """Plan at 'planning' stage gets updated to 'impl'."""
    issue = _make_issue(number=100, lifecycle_stage="planning")
    fake_issues = FakeGitHubIssues(issues={100: issue})
    ctx = context_for_test(cwd=tmp_path, issues=fake_issues)

    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="100", quiet=False)

    assert len(fake_issues.updated_bodies) == 1
    updated_body = fake_issues.updated_bodies[0][1]
    assert "lifecycle_stage: impl" in updated_body
