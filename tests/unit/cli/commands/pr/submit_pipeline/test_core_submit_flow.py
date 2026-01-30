"""Unit tests for _core_submit_flow pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    SubmitState,
    _core_submit_flow,
)
from erk.core.context import context_for_test
from erk_shared.gateway.git.abc import BranchDivergence
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails


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
    base: str = "main",
    body: str = "",
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Test PR",
        body=body,
        state="OPEN",
        base_ref_name=base,
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )


def test_github_auth_failure_returns_error(tmp_path: Path) -> None:
    """SubmitError(error_type='github_auth_failed') when not authenticated."""
    fake_github = FakeGitHub(authenticated=False)
    ctx = context_for_test(github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "github_auth_failed"


def test_no_commits_ahead_returns_error(tmp_path: Path) -> None:
    """SubmitError(error_type='no_commits') when zero commits ahead of parent."""
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "main"): 0},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=0,
                behind=0,
            )
        },
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "no_commits"


def test_branch_diverged_returns_error(tmp_path: Path) -> None:
    """Diverged + not force => error."""
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "main"): 3},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=True,
                ahead=3,
                behind=2,
            )
        },
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, force=False)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "branch_diverged"


def test_force_allows_diverged_push(tmp_path: Path) -> None:
    """force=True bypasses divergence check and creates PR."""
    pr = _pr_details(number=42, branch="feature")
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "main"): 3},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=True,
                ahead=3,
                behind=2,
            )
        },
        repository_roots={tmp_path: tmp_path},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, force=True)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.pr_number == 42


def test_auto_rebase_when_behind_remote(tmp_path: Path) -> None:
    """Calls pull_rebase() when behind remote."""
    pr = _pr_details(number=42, branch="feature")
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "main"): 1},
        # First call: behind=2, second call (after rebase): behind=0
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=1,
                behind=0,
            )
        },
        repository_roots={tmp_path: tmp_path},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitState)


def test_push_non_fast_forward_returns_error(tmp_path: Path) -> None:
    """RuntimeError('non-fast-forward') => diverged error."""
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "main"): 1},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=1,
                behind=0,
            )
        },
        push_to_remote_raises=RuntimeError("non-fast-forward update rejected"),
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "branch_diverged"


def test_push_generic_rejection_returns_error(tmp_path: Path) -> None:
    """RuntimeError('rejected') => diverged error."""
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "main"): 1},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=1,
                behind=0,
            )
        },
        push_to_remote_raises=RuntimeError("push Rejected by remote"),
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "branch_diverged"


def test_creates_new_pr_when_none_exists(tmp_path: Path) -> None:
    """was_created=True and PR number set when no existing PR."""
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "main"): 1},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=1,
                behind=0,
            )
        },
        repository_roots={tmp_path: tmp_path},
    )
    # No existing PR for branch; get_pr returns PRNotFound for pr 999 too
    fake_github = FakeGitHub()
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.was_created is True
    assert result.pr_number == 999  # FakeGitHub.create_pr returns 999


def test_parent_branch_no_pr_returns_error(tmp_path: Path) -> None:
    """Stacked PR with no parent PR => error."""
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "parent-branch"): 1},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=1,
                behind=0,
            )
        },
        repository_roots={tmp_path: tmp_path},
    )
    # No PR for either branch
    fake_github = FakeGitHub()
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(
        cwd=tmp_path,
        parent_branch="parent-branch",
        trunk_branch="main",
    )

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "parent_branch_no_pr"


def test_existing_pr_adds_footer_if_missing(tmp_path: Path) -> None:
    """Existing PR without footer gets footer added."""
    pr = _pr_details(number=42, branch="feature", body="Some PR body")
    fake_git = FakeGit(
        commits_ahead={(tmp_path, "main"): 1},
        branch_divergence={
            (tmp_path, "feature", "origin"): BranchDivergence(
                is_diverged=False,
                ahead=1,
                behind=0,
            )
        },
        repository_roots={tmp_path: tmp_path},
    )
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
        pr_details={42: pr},
    )
    ctx = context_for_test(git=fake_git, github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = _core_submit_flow(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.was_created is False
    assert result.pr_number == 42
    # Footer should have been added (body didn't contain "erk pr checkout")
    assert len(fake_github.updated_pr_bodies) == 1
    updated_body = fake_github.updated_pr_bodies[0][1]
    assert "erk pr checkout" in updated_body
