"""Tests for validate_pr pipeline step."""

from pathlib import Path

import pytest

from erk.cli.commands.land_pipeline import (
    LandError,
    LandState,
    make_initial_state,
    validate_pr,
)
from erk.cli.ensure import UserFacingCliError
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


def _resolved_state(tmp_path: Path, *, pr_details: PRDetails) -> LandState:
    """Create a LandState as if resolve_target has already run."""
    return LandState(
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
        branch=pr_details.head_ref_name,
        pr_number=pr_details.number,
        pr_details=pr_details,
        worktree_path=None,
        is_current_branch=False,
        use_graphite=False,
        target_child_branch=None,
        objective_number=None,
        plan_id=None,
        cleanup_confirmed=False,
        merged_pr_number=None,
    )


def test_passes_for_open_pr_targeting_trunk(tmp_path: Path) -> None:
    """validate_pr passes when PR is open and targets trunk."""
    pr_details = _make_pr_details(
        pr_number=42, branch="feature", state="OPEN", base_ref_name="main"
    )

    fake_git = FakeGit(default_branches={tmp_path: "main"})
    fake_github = FakeGitHub()

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    state = _resolved_state(tmp_path, pr_details=pr_details)
    result = validate_pr(ctx, state)

    assert not isinstance(result, LandError)
    # State unchanged (validate_pr is a validation-only step)
    assert result.pr_number == 42


def test_fails_for_closed_pr(tmp_path: Path) -> None:
    """validate_pr fails when PR is not open."""
    pr_details = _make_pr_details(
        pr_number=42, branch="feature", state="CLOSED", base_ref_name="main"
    )

    fake_git = FakeGit(default_branches={tmp_path: "main"})

    ctx = context_for_test(
        git=fake_git,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    state = _resolved_state(tmp_path, pr_details=pr_details)
    with pytest.raises(UserFacingCliError):
        validate_pr(ctx, state)


def test_fails_for_wrong_base_branch(tmp_path: Path) -> None:
    """validate_pr fails when PR targets non-trunk branch (non-Graphite)."""
    pr_details = _make_pr_details(
        pr_number=42,
        branch="feature",
        state="OPEN",
        base_ref_name="develop",  # Not trunk
    )

    fake_git = FakeGit(default_branches={tmp_path: "main"})

    ctx = context_for_test(
        git=fake_git,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    state = _resolved_state(tmp_path, pr_details=pr_details)
    with pytest.raises(UserFacingCliError):
        validate_pr(ctx, state)


def test_returns_error_for_none_pr_details(tmp_path: Path) -> None:
    """validate_pr returns LandError when pr_details is None."""
    fake_git = FakeGit(default_branches={tmp_path: "main"})

    ctx = context_for_test(
        git=fake_git,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=tmp_path,
    )

    state = make_initial_state(
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
    # pr_details is None in initial state
    result = validate_pr(ctx, state)

    assert isinstance(result, LandError)
    assert result.phase == "validate_pr"
    assert result.error_type == "no_pr_details"
