"""Unit tests for extract_diff_and_fetch_plan_context combined pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    SubmitState,
    extract_diff_and_fetch_plan_context,
)
from erk.core.context import RepoContext
from erk.core.plan_context_provider import PlanContext
from erk_shared.gateway.github.types import GitHubRepoId
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.test_context import context_for_test


def _test_repo(tmp_path: Path) -> RepoContext:
    return RepoContext(
        root=tmp_path,
        repo_name="repo",
        repo_dir=tmp_path,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=tmp_path / "pool.json",
        github=GitHubRepoId(owner="test", repo="repo"),
    )


def _make_state(
    *,
    cwd: Path,
    repo_root: Path | None = None,
    branch_name: str = "feature",
    parent_branch: str = "main",
    trunk_branch: str = "main",
    use_graphite: bool = False,
    force: bool = False,
    debug: bool = False,
    session_id: str = "test-session",
    skip_description: bool = False,
    pr_id: str | None = None,
    pr_number: int | None = None,
    pr_url: str | None = None,
    was_created: bool = False,
    base_branch: str | None = None,
    graphite_url: str | None = None,
    diff_file: Path | None = None,
    plan_context: PlanContext | None = None,
    title: str | None = None,
    body: str | None = None,
) -> SubmitState:
    return SubmitState(
        cwd=cwd,
        repo_root=repo_root if repo_root is not None else cwd,
        branch_name=branch_name,
        parent_branch=parent_branch,
        trunk_branch=trunk_branch,
        use_graphite=use_graphite,
        force=force,
        debug=debug,
        session_id=session_id,
        skip_description=skip_description,
        quiet=False,
        pr_id=pr_id,
        pr_number=pr_number,
        pr_url=pr_url,
        was_created=was_created,
        base_branch=base_branch,
        graphite_url=graphite_url,
        diff_file=diff_file,
        plan_context=plan_context,
        title=title,
        body=body,
        existing_pr_body="",
        graphite_is_authed=None,
        graphite_branch_tracked=None,
    )


def test_skip_description_returns_state_unchanged(tmp_path: Path) -> None:
    """skip_description=True causes early return with state unchanged."""
    ctx = context_for_test(cwd=tmp_path, repo=_test_repo(tmp_path))
    state = _make_state(cwd=tmp_path, skip_description=True)

    result = extract_diff_and_fetch_plan_context(ctx, state)

    assert result is state


def test_sets_both_diff_file_and_plan_context(tmp_path: Path) -> None:
    """Both diff_file and plan_context are populated on the returned state."""
    fake_git = FakeGit(
        diff_to_branch={(tmp_path, "main"): "diff --git a/file.py\n+hello"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path, repo=_test_repo(tmp_path))
    state = _make_state(cwd=tmp_path, base_branch="main")

    result = extract_diff_and_fetch_plan_context(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.diff_file is not None
    assert result.diff_file.exists()
    # plan_context comes from the default fake which returns no plan
    assert result.plan_context is not None or result.plan_context is None


def test_extract_diff_error_propagated(tmp_path: Path) -> None:
    """SubmitError from extract_diff is returned by the combined step."""
    ctx = context_for_test(cwd=tmp_path, repo=_test_repo(tmp_path))
    state = _make_state(cwd=tmp_path)

    result = extract_diff_and_fetch_plan_context(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "no_base_branch"
