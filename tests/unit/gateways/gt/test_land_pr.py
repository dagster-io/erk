"""Tests for single-PR landing helpers and workflow."""

from pathlib import Path

from erk_shared.gateway.github.types import PRDetails, PRNotFound, PullRequestInfo
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.operations.land_pr import execute_land_pr
from erk_shared.gateway.gt.types import LandPrError, LandPrSuccess
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.graphite import FakeGraphite
from tests.test_utils.test_context import context_for_test


def _make_pr_details(*, pr_number: int, branch: str, base_ref_name: str) -> PRDetails:
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        title=f"PR for {branch}",
        body=f"Body for {branch}",
        state="OPEN",
        base_ref_name=base_ref_name,
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )


def _make_pr_info(*, pr_number: int, branch: str) -> PullRequestInfo:
    return PullRequestInfo(
        number=pr_number,
        state="OPEN",
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        is_draft=False,
        title=f"PR for {branch}",
        checks_passing=None,
        owner="owner",
        repo="repo",
        head_branch=branch,
    )


def test_execute_land_pr_fails_when_child_pr_reparent_does_not_apply(tmp_path: Path) -> None:
    """Landing aborts before merge when a child PR base update silently no-ops."""
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-a"},
        default_branches={tmp_path: "main"},
        repository_roots={tmp_path: tmp_path},
    )
    fake_graphite = FakeGraphite(
        branches={
            "main": BranchMetadata.trunk("main", children=["feature-a"], commit_sha="main-sha"),
            "feature-a": BranchMetadata.branch(
                "feature-a",
                "main",
                children=["feature-b"],
                commit_sha="a-sha",
            ),
            "feature-b": BranchMetadata.branch("feature-b", "feature-a", commit_sha="b-sha"),
        }
    )
    parent_pr = _make_pr_details(pr_number=101, branch="feature-a", base_ref_name="main")
    child_pr = _make_pr_details(pr_number=102, branch="feature-b", base_ref_name="feature-a")
    fake_github = FakeLocalGitHub(
        prs={"feature-b": _make_pr_info(pr_number=102, branch="feature-b")},
        pr_details={101: parent_pr, 102: child_pr},
        prs_by_branch={"feature-a": parent_pr, "feature-b": child_pr},
        pr_base_update_should_apply=False,
    )
    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=fake_graphite,
        cwd=tmp_path,
    )

    result = render_events(execute_land_pr(ctx, tmp_path))

    assert isinstance(result, LandPrError)
    assert result.error_type == "child-pr-reparent-failed"
    assert fake_github.merged_prs == []


def test_execute_land_pr_reparents_github_only_child_before_merge(tmp_path: Path) -> None:
    """Landing discovers child PRs from GitHub even when Graphite does not know them."""
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-a"},
        default_branches={tmp_path: "main"},
        repository_roots={tmp_path: tmp_path},
    )
    fake_graphite = FakeGraphite(
        branches={
            "main": BranchMetadata.trunk("main", children=["feature-a"], commit_sha="main-sha"),
            "feature-a": BranchMetadata.branch("feature-a", "main", commit_sha="a-sha"),
        }
    )
    parent_pr = _make_pr_details(pr_number=101, branch="feature-a", base_ref_name="main")
    child_pr = _make_pr_details(pr_number=102, branch="feature-b", base_ref_name="feature-a")
    fake_github = FakeLocalGitHub(
        prs={"feature-b": _make_pr_info(pr_number=102, branch="feature-b")},
        pr_details={101: parent_pr, 102: child_pr},
        prs_by_branch={"feature-a": parent_pr, "feature-b": child_pr},
    )
    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=fake_graphite,
        cwd=tmp_path,
    )

    result = render_events(execute_land_pr(ctx, tmp_path))

    assert isinstance(result, LandPrSuccess)
    updated_child = fake_github.get_pr(tmp_path, 102)
    assert not isinstance(updated_child, PRNotFound)
    assert updated_child.base_ref_name == "main"
    assert fake_github.updated_pr_bases == [(102, "main")]
    assert fake_github.merged_prs == [101]
