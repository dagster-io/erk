"""Tests for resolve_target pipeline step."""

from pathlib import Path

import pytest

from erk.cli.commands.land_pipeline import (
    LandError,
    LandState,
    make_initial_state,
    resolve_target,
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
    is_cross_repository: bool = False,
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
        is_cross_repository=is_cross_repository,
        owner="owner",
        repo="repo",
    )


def _make_state(cwd: Path, *, target_arg: str | None = None, up_flag: bool = False) -> LandState:
    return make_initial_state(
        cwd=cwd,
        force=False,
        script=False,
        pull_flag=True,
        no_delete=False,
        up_flag=up_flag,
        dry_run=False,
        target_arg=target_arg,
        repo_root=cwd,
        main_repo_root=cwd,
    )


def test_resolves_current_branch(tmp_path: Path) -> None:
    """resolve_target populates state from current branch when target_arg is None."""
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

    state = _make_state(tmp_path)
    result = resolve_target(ctx, state)

    assert not isinstance(result, LandError)
    assert result.branch == branch
    assert result.pr_number == pr_number
    assert result.pr_details is not None
    assert result.pr_details.number == pr_number
    assert result.is_current_branch is True
    assert result.use_graphite is False
    assert result.worktree_path == tmp_path


def test_resolves_pr_by_number(tmp_path: Path) -> None:
    """resolve_target populates state from PR number."""
    branch = "feature-branch"
    pr_number = 123

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

    state = _make_state(tmp_path, target_arg="123")
    result = resolve_target(ctx, state)

    assert not isinstance(result, LandError)
    assert result.branch == branch
    assert result.pr_number == pr_number
    assert result.is_current_branch is False
    assert result.use_graphite is False


def test_resolves_branch_by_name(tmp_path: Path) -> None:
    """resolve_target populates state from branch name."""
    branch = "feature-branch"
    pr_number = 99

    pr_details = _make_pr_details(pr_number=pr_number, branch=branch)

    fake_git = FakeGit(
        current_branches={tmp_path: "other-branch"},
        default_branches={tmp_path: "main"},
    )
    fake_github = FakeGitHub(prs_by_branch={branch: pr_details})

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    state = _make_state(tmp_path, target_arg="feature-branch")
    result = resolve_target(ctx, state)

    assert not isinstance(result, LandError)
    assert result.branch == branch
    assert result.pr_number == pr_number
    assert result.is_current_branch is False


def test_returns_error_for_up_flag_with_pr(tmp_path: Path) -> None:
    """resolve_target returns LandError when --up is used with PR target."""
    pr_number = 123
    pr_details = _make_pr_details(pr_number=pr_number, branch="branch")

    fake_git = FakeGit(default_branches={tmp_path: "main"})
    fake_github = FakeGitHub(pr_details={pr_number: pr_details})

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    state = _make_state(tmp_path, target_arg="123", up_flag=True)
    result = resolve_target(ctx, state)

    assert isinstance(result, LandError)
    assert result.phase == "resolve_target"
    assert result.error_type == "up_with_pr"


def test_detached_head_fails(tmp_path: Path) -> None:
    """resolve_target fails when in detached HEAD state and no target."""
    fake_git = FakeGit(
        current_branches={tmp_path: None},
        default_branches={tmp_path: "main"},
    )

    ctx = context_for_test(
        git=fake_git,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    state = _make_state(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        resolve_target(ctx, state)

    assert exc_info.value.code == 1
