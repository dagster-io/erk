"""Tests for implement command retry detection and auto-reset.

Tests the _is_retry and _auto_reset helper functions that detect
previous implementation attempts and reset branches for retry.
"""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.implement import _auto_reset, _is_retry
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.fakes.gateway.time import FakeTime
from tests.test_utils.plan_helpers import format_plan_header_body_for_test
from tests.test_utils.test_context import context_for_test

BRANCH = "plnd/test-feature-01-15-1430"
PLAN_NUMBER = 42
MERGE_BASE_SHA = "deadbeef12345678"
BASE_REF = "master"


def _make_pr_body() -> str:
    """Create PR body with plan-header metadata."""
    header = format_plan_header_body_for_test(branch_name=BRANCH)
    plan_content = "# Test Plan\n\nSteps here."
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


def _build_ctx(
    tmp_path: Path,
    *,
    commits_ahead: int = 3,
    merge_base: str = MERGE_BASE_SHA,
):
    """Build ErkContext with configured fakes for retry tests."""
    git = FakeGit(
        current_branches={tmp_path: BRANCH},
        trunk_branches={tmp_path: "master"},
        commits_ahead={(tmp_path, f"origin/{BASE_REF}"): commits_ahead},
        merge_bases={(f"origin/{BASE_REF}", "HEAD"): merge_base},
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
    return ctx, git, fake_github


# --- _is_retry tests ---


def test_is_retry_true_with_commits_ahead(tmp_path: Path) -> None:
    """Detects retry when branch has commits ahead of base."""
    ctx, _, _ = _build_ctx(tmp_path, commits_ahead=3)
    assert _is_retry(ctx, str(PLAN_NUMBER)) is True


def test_is_retry_false_on_clean_branch(tmp_path: Path) -> None:
    """No retry when branch is at merge-base."""
    ctx, _, _ = _build_ctx(tmp_path, commits_ahead=0)
    assert _is_retry(ctx, str(PLAN_NUMBER)) is False


def test_is_retry_false_when_plan_not_found(tmp_path: Path) -> None:
    """No retry when plan doesn't exist."""
    git = FakeGit(
        current_branches={tmp_path: BRANCH},
        trunk_branches={tmp_path: "master"},
    )
    fake_github = FakeLocalGitHub()
    ctx = context_for_test(git=git, github=fake_github, cwd=tmp_path)
    assert _is_retry(ctx, "9999") is False


# --- _auto_reset tests ---


def test_auto_reset_resets_and_force_pushes(tmp_path: Path) -> None:
    """Auto-reset performs git reset, force push, and lifecycle update."""
    ctx, git, fake_github = _build_ctx(tmp_path, commits_ahead=5)

    _auto_reset(ctx, str(PLAN_NUMBER))

    # Verify git reset --hard
    assert len(git._reset_hard_calls) == 1
    assert git._reset_hard_calls[0] == (tmp_path, MERGE_BASE_SHA)

    # Verify force push
    assert len(git.pushed_branches) == 1
    pushed = git.pushed_branches[0]
    assert pushed.branch == BRANCH
    assert pushed.force is True
    assert pushed.set_upstream is False

    # Verify lifecycle comment
    assert len(fake_github.pr_comments) == 1
    pr_num, comment = fake_github.pr_comments[0]
    assert pr_num == PLAN_NUMBER
    assert "reset" in comment.lower()


def test_auto_reset_skips_when_plan_not_found(tmp_path: Path) -> None:
    """Auto-reset is a no-op when plan doesn't exist (graceful)."""
    git = FakeGit(
        current_branches={tmp_path: BRANCH},
        trunk_branches={tmp_path: "master"},
    )
    fake_github = FakeLocalGitHub()
    ctx = context_for_test(git=git, github=fake_github, cwd=tmp_path)

    _auto_reset(ctx, "9999")

    # No git mutations
    assert len(git._reset_hard_calls) == 0
    assert len(git.pushed_branches) == 0


def test_auto_reset_skips_when_merge_base_fails(tmp_path: Path) -> None:
    """Auto-reset is a no-op when merge-base computation fails."""
    git = FakeGit(
        current_branches={tmp_path: BRANCH},
        trunk_branches={tmp_path: "master"},
        commits_ahead={(tmp_path, f"origin/{BASE_REF}"): 2},
        # No merge_bases → returns None
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

    _auto_reset(ctx, str(PLAN_NUMBER))

    # No git mutations
    assert len(git._reset_hard_calls) == 0
    assert len(git.pushed_branches) == 0
