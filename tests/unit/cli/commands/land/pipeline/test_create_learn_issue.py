"""Tests for create_learn_issue execution pipeline step."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.land_pipeline import (
    LandError,
    LandState,
    create_learn_issue,
)
from erk.core.context import context_for_test
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend


def _execution_state(
    tmp_path: Path,
    *,
    plan_id: str | None = None,
    merged_pr_number: int | None = None,
) -> LandState:
    """Create LandState as if in execution pipeline."""
    return LandState(
        cwd=tmp_path,
        force=True,
        script=False,
        pull_flag=True,
        no_delete=False,
        up_flag=False,
        dry_run=False,
        target_arg=None,
        repo_root=tmp_path,
        main_repo_root=tmp_path,
        branch="feature",
        pr_number=42,
        pr_details=None,
        worktree_path=None,
        is_current_branch=False,
        use_graphite=False,
        target_child_branch=None,
        objective_number=None,
        plan_id=plan_id,
        cleanup_confirmed=True,
        merged_pr_number=merged_pr_number,
    )


def test_returns_state_unchanged_when_plan_id_none(tmp_path: Path) -> None:
    """No-op when plan_id is None — returns state unchanged."""
    fake_issues = FakeGitHubIssues(username="testuser")
    ctx = context_for_test(issues=fake_issues, cwd=tmp_path)
    state = _execution_state(tmp_path, plan_id=None, merged_pr_number=99)

    result = create_learn_issue(ctx, state)

    assert not isinstance(result, LandError)
    assert result is state
    assert len(fake_issues.created_issues) == 0


def test_returns_state_unchanged_when_merged_pr_none(tmp_path: Path) -> None:
    """No-op when merged_pr_number is None — returns state unchanged."""
    fake_issues = FakeGitHubIssues(username="testuser")
    ctx = context_for_test(issues=fake_issues, cwd=tmp_path)
    state = _execution_state(tmp_path, plan_id="100", merged_pr_number=None)

    result = create_learn_issue(ctx, state)

    assert not isinstance(result, LandError)
    assert result is state
    assert len(fake_issues.created_issues) == 0


def test_returns_state_after_creating_issue(tmp_path: Path) -> None:
    """With plan_id and merged_pr_number set, delegates to learn issue creation."""
    now = datetime(2024, 1, 1, tzinfo=UTC)
    pr = PRDetails(
        number=100,
        url="https://github.com/owner/repo/pull/100",
        title="Add feature",
        body="Test body",
        state="OPEN",
        base_ref_name="main",
        head_ref_name="feature",
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=True,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
        labels=("erk-plan",),
        created_at=now,
        updated_at=now,
    )
    fake_issues = FakeGitHubIssues(username="testuser", labels={"erk-pr", "erk-learn", "erk-plan"})
    fake_github = FakeGitHub(pr_details={100: pr}, issues_gateway=fake_issues)
    fake_time = FakeTime()
    plan_store = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        github=fake_github,
        issues=fake_issues,
        plan_store=plan_store,
        cwd=tmp_path,
    )
    state = _execution_state(tmp_path, plan_id="100", merged_pr_number=42)

    result = create_learn_issue(ctx, state)

    assert not isinstance(result, LandError)
    # State is returned unchanged (fire-and-forget)
    assert result is state
    # Learn issue was created
    assert len(fake_issues.created_issues) == 1
