"""Tests for land_learn module: learn issue creation logic."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.cli.commands.land_learn import (
    _create_learn_issue_impl,
    _create_learn_issue_with_sessions,
    _should_create_learn_issue,
)
from erk.cli.commands.land_pipeline import LandState
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig, LoadedConfig
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend


def _make_pr_details(
    *,
    pr_number: int,
    branch: str,
    title: str = "Test PR",
    labels: tuple[str, ...] = (),
) -> PRDetails:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        title=title,
        body="Test body",
        state="OPEN",
        base_ref_name="main",
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=True,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
        labels=labels,
        created_at=now,
        updated_at=now,
    )


def _land_state(
    tmp_path: Path,
    *,
    plan_id: str | None = None,
    merged_pr_number: int | None = None,
) -> LandState:
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


# ---------------------------------------------------------------------------
# _should_create_learn_issue
# ---------------------------------------------------------------------------


def test_returns_local_config_when_set(tmp_path: Path) -> None:
    """Local config prompt_learn_on_land=True overrides global."""
    ctx = context_for_test(
        local_config=LoadedConfig.test(prompt_learn_on_land=True),
        global_config=GlobalConfig.test(tmp_path, prompt_learn_on_land=False),
        cwd=tmp_path,
    )
    assert _should_create_learn_issue(ctx) is True


def test_falls_back_to_global_config_when_local_unset(tmp_path: Path) -> None:
    """When local_config.prompt_learn_on_land is None, falls back to global."""
    ctx = context_for_test(
        local_config=LoadedConfig.test(prompt_learn_on_land=None),
        global_config=GlobalConfig.test(tmp_path, prompt_learn_on_land=False),
        cwd=tmp_path,
    )
    assert _should_create_learn_issue(ctx) is False


def test_returns_true_when_both_unset(tmp_path: Path) -> None:
    """When local is None and global_config is None, returns True (safe default)."""
    ctx = context_for_test(
        local_config=LoadedConfig.test(prompt_learn_on_land=None),
        global_config=None,
        cwd=tmp_path,
    )
    assert _should_create_learn_issue(ctx) is True


# ---------------------------------------------------------------------------
# _create_learn_issue_with_sessions
# ---------------------------------------------------------------------------


def test_returns_early_when_plan_id_is_none(tmp_path: Path) -> None:
    """No-op when state.plan_id is None."""
    fake_issues = FakeGitHubIssues(username="testuser")
    ctx = context_for_test(issues=fake_issues, cwd=tmp_path)
    state = _land_state(tmp_path, plan_id=None, merged_pr_number=99)

    _create_learn_issue_with_sessions(ctx, state=state)

    assert len(fake_issues.created_issues) == 0


def test_returns_early_when_merged_pr_number_is_none(tmp_path: Path) -> None:
    """No-op when state.merged_pr_number is None."""
    fake_issues = FakeGitHubIssues(username="testuser")
    ctx = context_for_test(issues=fake_issues, cwd=tmp_path)
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=None)

    _create_learn_issue_with_sessions(ctx, state=state)

    assert len(fake_issues.created_issues) == 0


def test_shows_warning_on_exception(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exception in _create_learn_issue_impl is caught and shown as warning."""
    from erk.cli.commands import land_learn as learn_mod

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated network error")

    monkeypatch.setattr(learn_mod, "_create_learn_issue_impl", _raise)

    ctx = context_for_test(cwd=tmp_path)
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=99)

    # Should NOT raise — exception is caught
    _create_learn_issue_with_sessions(ctx, state=state)

    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert "simulated network error" in captured.err


# ---------------------------------------------------------------------------
# _create_learn_issue_impl
# ---------------------------------------------------------------------------


def test_skips_when_config_disabled(tmp_path: Path) -> None:
    """Returns early when prompt_learn_on_land is False."""
    fake_issues = FakeGitHubIssues(username="testuser")
    ctx = context_for_test(
        issues=fake_issues,
        local_config=LoadedConfig.test(prompt_learn_on_land=False),
        cwd=tmp_path,
    )
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=99)

    _create_learn_issue_impl(ctx, state=state)

    assert len(fake_issues.created_issues) == 0


def test_skips_for_erk_learn_plan(tmp_path: Path) -> None:
    """Returns early when plan has erk-learn label (cycle prevention)."""
    pr = _make_pr_details(
        pr_number=100,
        branch="feature",
        title="Learn: some plan",
        labels=("erk-plan", "erk-learn"),
    )
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeGitHub(pr_details={100: pr}, issues_gateway=fake_issues)
    fake_time = FakeTime()
    plan_store = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        github=fake_github,
        issues=fake_issues,
        plan_store=plan_store,
        cwd=tmp_path,
    )
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=99)

    _create_learn_issue_impl(ctx, state=state)

    assert len(fake_issues.created_issues) == 0


def test_skips_when_plan_not_found(tmp_path: Path) -> None:
    """Returns silently when get_plan returns PlanNotFound."""
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    fake_time = FakeTime()
    plan_store = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        github=fake_github,
        issues=fake_issues,
        plan_store=plan_store,
        cwd=tmp_path,
    )
    # plan_id "999" has no PR configured in FakeGitHub
    state = _land_state(tmp_path, plan_id="999", merged_pr_number=99)

    _create_learn_issue_impl(ctx, state=state)

    assert len(fake_issues.created_issues) == 0


def test_creates_issue_and_shows_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Happy path: plan found, not erk-learn, creates learn issue."""
    pr = _make_pr_details(
        pr_number=100,
        branch="feature",
        title="Add widgets",
        labels=("erk-plan",),
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
    state = _land_state(tmp_path, plan_id="100", merged_pr_number=42)

    _create_learn_issue_impl(ctx, state=state)

    # Issue should have been created
    assert len(fake_issues.created_issues) == 1
    title, _body, labels = fake_issues.created_issues[0]
    assert "Learn: Add widgets" in title
    assert "erk-learn" in labels

    # Plan content with source references is in the first comment
    assert len(fake_issues.added_comments) >= 1
    _plan_number, comment_body, _comment_id = fake_issues.added_comments[0]
    assert "#100" in comment_body
    assert "#42" in comment_body

    # Success output
    captured = capsys.readouterr()
    assert "Created learn issue" in captured.err
    assert "#100" in captured.err
