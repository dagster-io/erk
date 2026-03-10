"""Tests for resolve_plan_id pipeline step."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.land_pipeline import (
    LandError,
    LandState,
    resolve_pr_id,
)
from erk_shared.gateway.github.types import PRDetails
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.fakes.gateway.time import FakeTime
from tests.test_utils.test_context import context_for_test


def _make_pr_details(*, pr_number: int, branch: str) -> PRDetails:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        title="Test PR",
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
        created_at=now,
        updated_at=now,
    )


def _validation_state(tmp_path: Path, *, branch: str) -> LandState:
    """Create LandState as if resolve_target has run."""
    return LandState(
        cwd=tmp_path,
        force=False,
        script=False,
        pull_flag=True,
        no_delete=False,
        up_flag=False,
        dry_run=False,
        skip_learn=False,
        target_arg=None,
        repo_root=tmp_path,
        main_repo_root=tmp_path,
        branch=branch,
        pr_number=42,
        pr_details=None,
        worktree_path=None,
        is_current_branch=False,
        use_graphite=False,
        target_child_branch=None,
        objective_number=None,
        pr_id=None,
        cleanup_confirmed=False,
        merged_pr_number=None,
    )


def test_sets_plan_id_when_branch_has_plan(tmp_path: Path) -> None:
    """Branch resolves to a PR → plan_id is set to the PR number string."""
    branch = "plnd/my-feature"
    pr = _make_pr_details(pr_number=200, branch=branch)

    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeLocalGitHub(prs_by_branch={branch: pr}, issues_gateway=fake_issues)
    fake_time = FakeTime()
    plan_store = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        github=fake_github,
        issues=fake_issues,
        plan_store=plan_store,
        cwd=tmp_path,
    )

    state = _validation_state(tmp_path, branch=branch)
    result = resolve_pr_id(ctx, state)

    assert not isinstance(result, LandError)
    assert result.pr_id == "200"


def test_sets_pr_id_none_when_no_plan(tmp_path: Path) -> None:
    """Branch has no PR → pr_id is None."""
    fake_issues = FakeGitHubIssues(username="testuser")
    fake_github = FakeLocalGitHub(issues_gateway=fake_issues)
    fake_time = FakeTime()
    plan_store = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        github=fake_github,
        issues=fake_issues,
        plan_store=plan_store,
        cwd=tmp_path,
    )

    state = _validation_state(tmp_path, branch="no-pr-branch")
    result = resolve_pr_id(ctx, state)

    assert not isinstance(result, LandError)
    assert result.pr_id is None
