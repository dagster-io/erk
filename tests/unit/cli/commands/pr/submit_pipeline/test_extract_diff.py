"""Unit tests for extract_diff pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    SubmitState,
    extract_diff,
)
from erk.core.context import context_for_test
from erk_shared.gateway.git.fake import FakeGit


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


def test_no_base_branch_returns_error(tmp_path: Path) -> None:
    """SubmitError(error_type='no_base_branch') when base_branch is None."""
    fake_git = FakeGit()
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, base_branch=None)

    result = extract_diff(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "no_base_branch"


def test_writes_scratch_file(tmp_path: Path) -> None:
    """diff_file path set and file exists after extraction."""
    fake_git = FakeGit(
        diff_to_branch={(tmp_path, "main"): "diff --git a/file.py\n+hello"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, base_branch="main")

    result = extract_diff(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.diff_file is not None
    assert result.diff_file.exists()
    content = result.diff_file.read_text()
    assert "hello" in content
