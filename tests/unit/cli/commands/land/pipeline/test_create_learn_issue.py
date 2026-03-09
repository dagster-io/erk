"""Tests for create_learn_pr execution pipeline step."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.cli.commands.land_pipeline import (
    LandError,
    LandState,
    create_learn_pr,
)
from erk.core.context import context_for_test
from erk_shared.fakes.git import FakeGit
from erk_shared.fakes.github import FakeLocalGitHub
from erk_shared.fakes.github_issues import FakeGitHubIssues
from erk_shared.fakes.time import FakeTime
from erk_shared.gateway.github.types import PRDetails
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


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
        skip_learn=False,
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
    fake_github = FakeLocalGitHub(issues_gateway=fake_issues)
    ctx = context_for_test(github=fake_github, issues=fake_issues, cwd=tmp_path)
    state = _execution_state(tmp_path, plan_id=None, merged_pr_number=99)

    result = create_learn_pr(ctx, state)

    assert not isinstance(result, LandError)
    assert result is state
    assert len(fake_github.created_prs) == 0


def test_returns_state_unchanged_when_merged_pr_none(tmp_path: Path) -> None:
    """No-op when merged_pr_number is None — returns state unchanged."""
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeLocalGitHub(issues_gateway=fake_issues)
    ctx = context_for_test(github=fake_github, issues=fake_issues, cwd=tmp_path)
    state = _execution_state(tmp_path, plan_id="100", merged_pr_number=None)

    result = create_learn_pr(ctx, state)

    assert not isinstance(result, LandError)
    assert result is state
    assert len(fake_github.created_prs) == 0


def test_returns_state_after_creating_pr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With plan_id and merged_pr_number set, delegates to learn PR creation."""
    from erk.cli.commands import land_learn as learn_mod

    now = datetime(2024, 1, 1, tzinfo=UTC)
    session_id = "aaaa1111-2222-3333-4444-555566667777"
    body = format_plan_header_body_for_test(created_from_session=session_id)
    pr = PRDetails(
        number=100,
        url="https://github.com/owner/repo/pull/100",
        title="Add feature",
        body=body,
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
    fake_github = FakeLocalGitHub(pr_details={100: pr}, issues_gateway=fake_issues)
    fake_time = FakeTime()
    fake_git = FakeGit(trunk_branches={tmp_path: "main"})
    plan_store = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        issues=fake_issues,
        plan_store=plan_store,
        time=fake_time,
        cwd=tmp_path,
    )
    state = _execution_state(tmp_path, plan_id="100", merged_pr_number=42)

    # Patch _log_session_discovery to return non-empty xml_files
    # so the skip-empty-sessions guard is not triggered
    stub_xml = {".erk/impl-context/sessions/planning-aaaa1111.xml": "<session>data</session>"}

    def _fake_log_session_discovery(*_args: object, **_kwargs: object) -> dict[str, str]:
        return stub_xml

    monkeypatch.setattr(learn_mod, "_log_session_discovery", _fake_log_session_discovery)

    result = create_learn_pr(ctx, state)

    assert not isinstance(result, LandError)
    # State is returned unchanged (fire-and-forget)
    assert result is state
    # Learn draft PR was created
    assert len(fake_github.created_prs) == 1
