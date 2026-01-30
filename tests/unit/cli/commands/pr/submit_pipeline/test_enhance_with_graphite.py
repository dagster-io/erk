"""Unit tests for enhance_with_graphite pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitState,
    enhance_with_graphite,
)
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata


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
    pr_number: int | None = 42,
    pr_url: str | None = "https://github.com/owner/repo/pull/42",
    was_created: bool = False,
    base_branch: str | None = "main",
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


def _graphite_config() -> GlobalConfig:
    return GlobalConfig(
        erk_root=Path("/test/erks"),
        use_graphite=True,
        shell_setup_complete=False,
        github_planning=True,
    )


def test_noop_when_graphite_url_already_set(tmp_path: Path) -> None:
    """Returns state unchanged when graphite_url is already populated."""
    ctx = context_for_test(cwd=tmp_path)
    state = _make_state(
        cwd=tmp_path,
        graphite_url="https://app.graphite.com/github/pr/owner/repo/42",
    )

    result = enhance_with_graphite(ctx, state)

    assert isinstance(result, SubmitState)
    assert result is state  # Exact same object returned


def test_noop_when_use_graphite_false(tmp_path: Path) -> None:
    """Returns state unchanged when use_graphite=False."""
    ctx = context_for_test(cwd=tmp_path)
    state = _make_state(cwd=tmp_path, use_graphite=False)

    result = enhance_with_graphite(ctx, state)

    assert isinstance(result, SubmitState)
    assert result is state


def test_skips_when_not_authenticated(tmp_path: Path) -> None:
    """No submit called when Graphite is not authenticated."""
    fake_graphite = FakeGraphite(authenticated=False)
    ctx = context_for_test(
        graphite=fake_graphite,
        cwd=tmp_path,
        global_config=_graphite_config(),
    )
    state = _make_state(cwd=tmp_path)

    result = enhance_with_graphite(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.graphite_url is None
    assert len(fake_graphite.submit_stack_calls) == 0


def test_skips_when_branch_not_tracked(tmp_path: Path) -> None:
    """No submit called when branch is not in Graphite's tracked branches."""
    fake_graphite = FakeGraphite(branches={})  # No branches tracked
    fake_git = FakeGit(repository_roots={tmp_path: tmp_path})
    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        cwd=tmp_path,
        global_config=_graphite_config(),
    )
    state = _make_state(cwd=tmp_path)

    result = enhance_with_graphite(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.graphite_url is None
    assert len(fake_graphite.submit_stack_calls) == 0


def test_handles_submit_error_gracefully(tmp_path: Path) -> None:
    """RuntimeError from submit_stack => warning, not SubmitError."""
    fake_graphite = FakeGraphite(
        branches={
            "feature": BranchMetadata(
                name="feature",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            )
        },
        submit_stack_raises=RuntimeError("unexpected error"),
    )
    fake_git = FakeGit(repository_roots={tmp_path: tmp_path})
    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        cwd=tmp_path,
        global_config=_graphite_config(),
    )
    state = _make_state(cwd=tmp_path)

    result = enhance_with_graphite(ctx, state)

    # Should NOT be a SubmitError - errors are handled gracefully
    assert isinstance(result, SubmitState)
    assert result.graphite_url is None


def test_success_sets_graphite_url(tmp_path: Path) -> None:
    """graphite_url populated on successful submit."""
    fake_graphite = FakeGraphite(
        branches={
            "feature": BranchMetadata(
                name="feature",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            )
        },
    )
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        cwd=tmp_path,
        global_config=_graphite_config(),
    )
    state = _make_state(cwd=tmp_path)

    result = enhance_with_graphite(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.graphite_url is not None
    assert "graphite" in result.graphite_url
    assert len(fake_graphite.submit_stack_calls) == 1
