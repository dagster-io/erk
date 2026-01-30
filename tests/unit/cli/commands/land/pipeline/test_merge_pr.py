"""Tests for merge_pr execution pipeline step."""

from pathlib import Path

from erk.cli.commands.land_pipeline import (
    LandError,
    LandState,
    merge_pr,
)
from erk.core.context import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason


def _make_pr_details(
    *,
    pr_number: int,
    branch: str,
    state: str = "OPEN",
    base_ref_name: str = "main",
) -> PRDetails:
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        title="Test PR",
        body="Test body",
        state=state,
        base_ref_name=base_ref_name,
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )


def _execution_state(
    tmp_path: Path,
    *,
    pr_number: int,
    branch: str,
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
        branch=branch,
        pr_number=pr_number,
        pr_details=None,  # Re-fetched by merge_pr
        worktree_path=None,
        is_current_branch=False,
        use_graphite=False,
        target_child_branch=None,
        objective_number=None,
        plan_issue_number=None,
        cleanup_confirmed=True,
        merged_pr_number=None,
    )


def test_merges_pr_via_github_api(tmp_path: Path) -> None:
    """merge_pr merges via GitHub API when not using Graphite."""
    branch = "feature-branch"
    pr_number = 42

    pr_details = _make_pr_details(pr_number=pr_number, branch=branch)
    fake_git = FakeGit(default_branches={tmp_path: "main"})
    fake_github = FakeGitHub(
        pr_details={pr_number: pr_details},
        merge_should_succeed=True,
    )

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    state = _execution_state(tmp_path, pr_number=pr_number, branch=branch)
    result = merge_pr(ctx, state)

    assert not isinstance(result, LandError)
    assert result.merged_pr_number == pr_number


def test_returns_error_on_merge_failure(tmp_path: Path) -> None:
    """merge_pr returns LandError when GitHub merge fails."""
    branch = "feature-branch"
    pr_number = 42

    pr_details = _make_pr_details(pr_number=pr_number, branch=branch)
    fake_git = FakeGit(default_branches={tmp_path: "main"})
    fake_github = FakeGitHub(
        pr_details={pr_number: pr_details},
        merge_should_succeed=False,
    )

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    state = _execution_state(tmp_path, pr_number=pr_number, branch=branch)
    result = merge_pr(ctx, state)

    assert isinstance(result, LandError)
    assert result.phase == "merge_pr"
    assert result.error_type == "github_merge_failed"
