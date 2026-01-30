"""Tests for run_execution_pipeline.

These tests verify pipeline mechanics (step chaining, error short-circuit).
Full cleanup_and_navigate behavior is tested separately in existing land command tests.
"""

from pathlib import Path

from erk.cli.commands.land_pipeline import (
    LandError,
    make_execution_state,
    merge_pr,
    run_execution_pipeline,
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


def test_merge_pr_step_succeeds(tmp_path: Path) -> None:
    """merge_pr step merges via GitHub API and populates merged_pr_number."""
    branch = "feature-branch"
    pr_number = 42

    pr_details = _make_pr_details(pr_number=pr_number, branch=branch)

    fake_git = FakeGit(
        current_branches={tmp_path: "main"},
        default_branches={tmp_path: "main"},
    )
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

    state = make_execution_state(
        cwd=tmp_path,
        pr_number=pr_number,
        branch=branch,
        worktree_path=None,
        is_current_branch=False,
        objective_number=None,
        use_graphite=False,
        pull_flag=True,
        no_delete=False,
        script=False,
        target_child_branch=None,
    )

    result = merge_pr(ctx, state)

    assert not isinstance(result, LandError)
    assert result.merged_pr_number == pr_number


def test_execution_pipeline_stops_on_merge_error(tmp_path: Path) -> None:
    """Execution pipeline returns error when merge fails (short-circuits remaining steps)."""
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

    state = make_execution_state(
        cwd=tmp_path,
        pr_number=pr_number,
        branch=branch,
        worktree_path=None,
        is_current_branch=False,
        objective_number=None,
        use_graphite=False,
        pull_flag=True,
        no_delete=False,
        script=False,
        target_child_branch=None,
    )

    result = run_execution_pipeline(ctx, state)

    assert isinstance(result, LandError)
    assert result.phase == "merge_pr"
    assert "Merge failed" in result.message
