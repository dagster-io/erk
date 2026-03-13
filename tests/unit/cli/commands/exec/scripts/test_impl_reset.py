"""Tests for impl-reset exec CLI command.

Tests the branch reset functionality for implementation retry.
Uses ErkContext via context_for_test() for dependency injection with PlannedPRBackend.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.impl_reset import impl_reset
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.fakes.gateway.time import FakeTime
from tests.test_utils.plan_helpers import format_plan_header_body_for_test
from tests.test_utils.test_context import context_for_test

BRANCH = "plnd/test-feature-01-15-1430"
PLAN_NUMBER = 123
MERGE_BASE_SHA = "abc123def456"
BASE_REF = "master"


def _make_pr_body(*, lifecycle_stage: str = "impl") -> str:
    """Create a PR body with plan-header metadata including base_ref_name."""
    header = format_plan_header_body_for_test(
        branch_name=BRANCH,
        lifecycle_stage=lifecycle_stage,
    )
    plan_content = "# Test Plan\n\nSome implementation steps."
    return (
        "<details open>\n<summary>Plan</summary>\n\n" + plan_content + "\n\n</details>\n\n" + header
    )


def _make_pr_details(*, base_ref_name: str = BASE_REF) -> PRDetails:
    """Create PRDetails for the test plan PR."""
    now = datetime.now(UTC)
    return PRDetails(
        number=PLAN_NUMBER,
        url=f"https://github.com/test/repo/pull/{PLAN_NUMBER}",
        title="[erk-pr] Test Feature",
        body=_make_pr_body(),
        state="OPEN",
        is_draft=True,
        base_ref_name=base_ref_name,
        head_ref_name=BRANCH,
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
        labels=("erk-pr",),
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def _make_pr_info() -> PullRequestInfo:
    """Create PullRequestInfo for branch lookup."""
    return PullRequestInfo(
        number=PLAN_NUMBER,
        state="OPEN",
        url=f"https://github.com/test/repo/pull/{PLAN_NUMBER}",
        is_draft=True,
        title="[erk-pr] Test Feature",
        checks_passing=None,
        owner="test-owner",
        repo="test-repo",
        head_branch=BRANCH,
    )


def _build_context(
    tmp_path: Path,
    *,
    commits_ahead: int = 3,
    merge_base: str = MERGE_BASE_SHA,
    base_ref_name: str = BASE_REF,
) -> tuple[FakeGit, FakeLocalGitHub]:
    """Build test context with configured git and github fakes."""
    git = FakeGit(
        current_branches={tmp_path: BRANCH},
        trunk_branches={tmp_path: "master"},
        commits_ahead={(tmp_path, f"origin/{base_ref_name}"): commits_ahead},
        merge_bases={(f"origin/{base_ref_name}", "HEAD"): merge_base},
    )

    pr_details = {PLAN_NUMBER: _make_pr_details(base_ref_name=base_ref_name)}
    prs = {BRANCH: _make_pr_info()}

    fake_github = FakeLocalGitHub(
        pr_details=pr_details,
        prs=prs,
    )

    return git, fake_github


# --- Success cases ---


def test_reset_with_implementation_commits(tmp_path: Path) -> None:
    """Reset succeeds when branch has commits beyond merge-base."""
    git, fake_github = _build_context(tmp_path, commits_ahead=3)
    fake_issues = FakeGitHubIssues()
    fake_time = FakeTime()
    backend = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        git=git,
        github=fake_github,
        issues=fake_issues,
        plan_store=backend,
        cwd=tmp_path,
        repo=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        impl_reset,
        ["--plan-number", str(PLAN_NUMBER)],
        obj=ctx,
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["plan_number"] == PLAN_NUMBER
    assert data["reset_to"] == MERGE_BASE_SHA
    assert data["lifecycle_stage"] == "planned"

    # Verify git operations
    assert len(git._reset_hard_calls) == 1
    assert git._reset_hard_calls[0] == (tmp_path, MERGE_BASE_SHA)

    # Verify force push
    assert len(git.pushed_branches) == 1
    pushed = git.pushed_branches[0]
    assert pushed.branch == BRANCH
    assert pushed.force is True

    # Verify lifecycle comment was posted
    assert len(fake_github.pr_comments) == 1


def test_reset_no_commits_beyond_merge_base(tmp_path: Path) -> None:
    """No-op when branch is already at merge-base."""
    git, fake_github = _build_context(tmp_path, commits_ahead=0)
    fake_issues = FakeGitHubIssues()
    fake_time = FakeTime()
    backend = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        git=git,
        github=fake_github,
        issues=fake_issues,
        plan_store=backend,
        cwd=tmp_path,
        repo=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        impl_reset,
        ["--plan-number", str(PLAN_NUMBER)],
        obj=ctx,
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert "no reset needed" in data["message"]

    # Verify NO git mutations
    assert len(git._reset_hard_calls) == 0
    assert len(git.pushed_branches) == 0


def test_reset_auto_detect_plan_number(tmp_path: Path) -> None:
    """Auto-detects plan number from current branch when --plan-number omitted."""
    git, fake_github = _build_context(tmp_path, commits_ahead=2)
    fake_issues = FakeGitHubIssues()
    fake_time = FakeTime()
    backend = PlannedPRBackend(fake_github, fake_issues, time=fake_time)

    ctx = context_for_test(
        git=git,
        github=fake_github,
        issues=fake_issues,
        plan_store=backend,
        cwd=tmp_path,
        repo=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(impl_reset, [], obj=ctx)

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["plan_number"] == PLAN_NUMBER


# --- Error cases ---


def test_reset_not_on_branch(tmp_path: Path) -> None:
    """Error when in detached HEAD state."""
    git = FakeGit(current_branches={tmp_path: None})

    ctx = context_for_test(git=git, cwd=tmp_path, repo=tmp_path)

    runner = CliRunner()
    result = runner.invoke(impl_reset, [], obj=ctx)

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "no-branch"


def test_reset_no_plan_for_branch(tmp_path: Path) -> None:
    """Error when branch has no associated plan PR."""
    git = FakeGit(
        current_branches={tmp_path: "feature/no-plan"},
        trunk_branches={tmp_path: "master"},
    )
    fake_github = FakeLocalGitHub()

    ctx = context_for_test(git=git, github=fake_github, cwd=tmp_path, repo=tmp_path)

    runner = CliRunner()
    result = runner.invoke(impl_reset, [], obj=ctx)

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "no-plan-found"


def test_reset_merge_base_fails(tmp_path: Path) -> None:
    """Error when merge-base computation fails."""
    git = FakeGit(
        current_branches={tmp_path: BRANCH},
        trunk_branches={tmp_path: "master"},
        commits_ahead={(tmp_path, f"origin/{BASE_REF}"): 2},
        # No merge_bases entry → get_merge_base returns None
    )

    pr_details = {PLAN_NUMBER: _make_pr_details()}
    prs = {BRANCH: _make_pr_info()}
    fake_github = FakeLocalGitHub(pr_details=pr_details, prs=prs)
    fake_issues = FakeGitHubIssues()
    backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())

    ctx = context_for_test(
        git=git,
        github=fake_github,
        issues=fake_issues,
        plan_store=backend,
        cwd=tmp_path,
        repo=tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        impl_reset,
        ["--plan-number", str(PLAN_NUMBER)],
        obj=ctx,
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "merge-base-failed"


def test_reset_plan_not_found(tmp_path: Path) -> None:
    """Error when plan number doesn't exist."""
    git = FakeGit(
        current_branches={tmp_path: BRANCH},
        trunk_branches={tmp_path: "master"},
    )
    fake_github = FakeLocalGitHub()

    ctx = context_for_test(git=git, github=fake_github, cwd=tmp_path, repo=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        impl_reset,
        ["--plan-number", "9999"],
        obj=ctx,
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "plan-not-found"
