"""Unit tests for _execute_simple_land (non-Graphite mode)."""

from pathlib import Path

import pytest

from erk.cli.commands.land_cmd import _execute_simple_land
from erk.core.context import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails


def test_execute_simple_land_merges_pr_without_graphite(tmp_path: Path) -> None:
    """Test that _execute_simple_land merges a PR using GitHub API only."""
    repo_root = tmp_path
    branch = "feature-branch"
    pr_number = 123

    # Create PR details
    pr_details = PRDetails(
        number=pr_number,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Test body",
        state="OPEN",
        base_ref_name="main",
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )

    fake_git = FakeGit(
        default_branches={repo_root: "main"},
    )

    fake_github = FakeGitHub(
        pr_details={pr_number: pr_details},
    )

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=repo_root,
    )

    # Execute simple land
    result = _execute_simple_land(ctx, repo_root=repo_root, branch=branch, pr_details=pr_details)

    # Verify PR was merged
    assert result == pr_number
    assert pr_number in fake_github.merged_prs


def test_execute_simple_land_fails_if_pr_not_open(tmp_path: Path) -> None:
    """Test that _execute_simple_land fails if PR is not open."""
    repo_root = tmp_path
    branch = "feature-branch"
    pr_number = 123

    # Create closed PR details
    pr_details = PRDetails(
        number=pr_number,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Test body",
        state="MERGED",
        base_ref_name="main",
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )

    fake_git = FakeGit(
        default_branches={repo_root: "main"},
    )

    fake_github = FakeGitHub()

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=repo_root,
    )

    # Execute simple land should fail
    try:
        _execute_simple_land(ctx, repo_root=repo_root, branch=branch, pr_details=pr_details)
        pytest.fail("Expected SystemExit")
    except SystemExit as e:
        assert e.code == 1


def test_execute_simple_land_fails_if_pr_not_targeting_trunk(tmp_path: Path) -> None:
    """Test that _execute_simple_land fails if PR base is not trunk."""
    repo_root = tmp_path
    branch = "feature-branch"
    pr_number = 123

    # Create PR targeting non-trunk branch
    pr_details = PRDetails(
        number=pr_number,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Test body",
        state="OPEN",
        base_ref_name="some-other-branch",  # Not trunk
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )

    fake_git = FakeGit(
        default_branches={repo_root: "main"},
    )

    fake_github = FakeGitHub()

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=repo_root,
    )

    # Execute simple land should fail
    try:
        _execute_simple_land(ctx, repo_root=repo_root, branch=branch, pr_details=pr_details)
        pytest.fail("Expected SystemExit")
    except SystemExit as e:
        assert e.code == 1
