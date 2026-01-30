"""Unit tests for _graphite_first_flow pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    SubmitState,
    _graphite_first_flow,
)
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite


def _make_state(
    *,
    cwd: Path,
    repo_root: Path | None = None,
    branch_name: str = "feature",
    parent_branch: str = "main",
    trunk_branch: str = "main",
    use_graphite: bool = True,
    force: bool = False,
    debug: bool = False,
    session_id: str = "test-session",
    issue_number: int | None = None,
    pr_number: int | None = None,
    pr_url: str | None = None,
    was_created: bool = False,
    base_branch: str | None = None,
    graphite_url: str | None = None,
    diff_file: Path | None = None,
    plan_context: None = None,
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
        issue_number=issue_number,
        pr_number=pr_number,
        pr_url=pr_url,
        was_created=was_created,
        base_branch=base_branch,
        graphite_url=graphite_url,
        diff_file=diff_file,
        plan_context=plan_context,
        title=title,
        body=body,
    )


def _pr_details(
    *,
    number: int = 42,
    branch: str = "feature",
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Test PR",
        body="",
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


def test_submit_failure_returns_error(tmp_path: Path) -> None:
    """SubmitError(error_type='graphite_submit_failed') on RuntimeError."""
    fake_graphite = FakeGraphite(
        submit_stack_raises=RuntimeError("gt submit failed"),
    )
    global_config = GlobalConfig(
        erk_root=Path("/test/erks"),
        use_graphite=True,
        shell_setup_complete=False,
        github_planning=True,
    )
    ctx = context_for_test(
        graphite=fake_graphite,
        cwd=tmp_path,
        global_config=global_config,
    )
    state = _make_state(cwd=tmp_path)

    result = _graphite_first_flow(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "graphite_submit_failed"


def test_pr_not_found_after_submit_returns_error(tmp_path: Path) -> None:
    """SubmitError(error_type='pr_not_found') when no PR after gt submit."""
    fake_graphite = FakeGraphite()
    fake_github = FakeGitHub()  # No PRs configured
    global_config = GlobalConfig(
        erk_root=Path("/test/erks"),
        use_graphite=True,
        shell_setup_complete=False,
        github_planning=True,
    )
    ctx = context_for_test(
        graphite=fake_graphite,
        github=fake_github,
        cwd=tmp_path,
        global_config=global_config,
    )
    state = _make_state(cwd=tmp_path)

    result = _graphite_first_flow(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "pr_not_found"


def test_success(tmp_path: Path) -> None:
    """PR number + graphite URL + was_created=True on success."""
    pr = _pr_details(number=42, branch="feature")
    fake_graphite = FakeGraphite()
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
    )
    fake_git = FakeGit(
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
        repository_roots={tmp_path: tmp_path},
    )
    global_config = GlobalConfig(
        erk_root=Path("/test/erks"),
        use_graphite=True,
        shell_setup_complete=False,
        github_planning=True,
    )
    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        github=fake_github,
        cwd=tmp_path,
        global_config=global_config,
    )
    state = _make_state(cwd=tmp_path)

    result = _graphite_first_flow(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.pr_number == 42
    assert result.was_created is True
    assert result.graphite_url is not None
    assert "graphite" in result.graphite_url
