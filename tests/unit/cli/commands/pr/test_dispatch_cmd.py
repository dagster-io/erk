"""Unit tests for dispatch_cmd._detect_plan_number_from_context."""

from pathlib import Path

from erk.cli.commands.pr.dispatch_cmd import _detect_plan_number_from_context
from erk_shared.context.testing import context_for_test
from erk_shared.context.types import RepoContext
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.types import PRDetails


def _repo_context(tmp_path: Path) -> RepoContext:
    return RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=tmp_path / ".erk" / "repos" / "test-repo",
        worktrees_dir=tmp_path / ".erk" / "repos" / "test-repo" / "worktrees",
        pool_json_path=tmp_path / ".erk" / "repos" / "test-repo" / "pool.json",
    )


def _make_pr_details(*, number: int, branch: str) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        title=f"Plan #{number}",
        body="plan body",
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
        labels=("erk-plan",),
    )


def test_fallback_to_plan_backend_when_no_impl_dir(tmp_path: Path) -> None:
    """When resolve_impl_dir returns None, falls back to plan_backend.resolve_plan_id_for_branch."""
    branch = "plnd/fix-something-01-01-1200"
    pr_details = _make_pr_details(number=42, branch=branch)

    github = FakeLocalGitHub(prs_by_branch={branch: pr_details})
    ctx = context_for_test(github=github, cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    result = _detect_plan_number_from_context(ctx, repo, branch_name=branch)

    assert result == 42


def test_returns_none_when_no_impl_dir_and_no_plan_backend_match(tmp_path: Path) -> None:
    """When both resolve_impl_dir and plan_backend return nothing, returns None."""
    ctx = context_for_test(cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    result = _detect_plan_number_from_context(ctx, repo, branch_name="feature/unrelated")

    assert result is None


def test_returns_none_when_branch_is_none(tmp_path: Path) -> None:
    """When branch_name is None, the fallback path is skipped and returns None."""
    ctx = context_for_test(cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    result = _detect_plan_number_from_context(ctx, repo, branch_name=None)

    assert result is None
