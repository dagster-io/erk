"""Tests for run_validation_pipeline."""

from pathlib import Path

import pytest

from erk.cli.commands.land_pipeline import (
    LandError,
    make_initial_state,
    run_validation_pipeline,
)
from erk.core.context import context_for_test
from erk_shared.gateway.git.abc import WorktreeInfo
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


def test_full_validation_pipeline_succeeds(tmp_path: Path) -> None:
    """Full validation pipeline runs all steps and returns populated state."""
    branch = "feature-branch"
    pr_number = 42

    pr_details = _make_pr_details(pr_number=pr_number, branch=branch)
    worktree = WorktreeInfo(path=tmp_path, branch=branch, is_root=True)

    fake_git = FakeGit(
        current_branches={tmp_path: branch},
        worktrees={tmp_path: [worktree]},
        default_branches={tmp_path: "main"},
    )
    fake_github = FakeGitHub(prs_by_branch={branch: pr_details})

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    initial_state = make_initial_state(
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
    )

    result = run_validation_pipeline(ctx, initial_state)

    assert not isinstance(result, LandError)
    assert result.branch == branch
    assert result.pr_number == pr_number
    assert result.pr_details is not None
    assert result.is_current_branch is True
    assert result.cleanup_confirmed is True  # force=True skips confirmation


def test_validation_pipeline_stops_on_error(tmp_path: Path) -> None:
    """Pipeline stops at first error (resolve_target fails for detached HEAD)."""
    fake_git = FakeGit(
        current_branches={tmp_path: None},  # Detached HEAD
        default_branches={tmp_path: "main"},
    )

    ctx = context_for_test(
        git=fake_git,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    initial_state = make_initial_state(
        cwd=tmp_path,
        force=False,
        script=False,
        pull_flag=True,
        no_delete=False,
        up_flag=False,
        dry_run=False,
        target_arg=None,
        repo_root=tmp_path,
        main_repo_root=tmp_path,
    )

    # resolve_target raises SystemExit for detached HEAD
    with pytest.raises(SystemExit) as exc_info:
        run_validation_pipeline(ctx, initial_state)

    assert exc_info.value.code == 1


def test_validation_pipeline_with_pr_target(tmp_path: Path) -> None:
    """Validation pipeline resolves PR by number and validates."""
    branch = "feature-branch"
    pr_number = 99

    pr_details = _make_pr_details(pr_number=pr_number, branch=branch)

    fake_git = FakeGit(
        current_branches={tmp_path: "other-branch"},
        default_branches={tmp_path: "main"},
    )
    fake_github = FakeGitHub(pr_details={pr_number: pr_details})

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    initial_state = make_initial_state(
        cwd=tmp_path,
        force=True,
        script=False,
        pull_flag=True,
        no_delete=False,
        up_flag=False,
        dry_run=False,
        target_arg="99",
        repo_root=tmp_path,
        main_repo_root=tmp_path,
    )

    result = run_validation_pipeline(ctx, initial_state)

    assert not isinstance(result, LandError)
    assert result.branch == branch
    assert result.pr_number == pr_number
    assert result.is_current_branch is False
