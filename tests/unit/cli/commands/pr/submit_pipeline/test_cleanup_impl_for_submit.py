"""Unit tests for cleanup_impl_for_submit pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitState,
    cleanup_impl_for_submit,
)
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.test_context import context_for_test


def _make_state(
    *,
    cwd: Path,
    repo_root: Path | None = None,
    branch_name: str = "feature",
) -> SubmitState:
    return SubmitState(
        cwd=cwd,
        repo_root=repo_root if repo_root is not None else cwd,
        branch_name=branch_name,
        parent_branch="main",
        trunk_branch="main",
        use_graphite=True,
        force=False,
        debug=False,
        session_id="test-session",
        skip_description=False,
        quiet=False,
        pr_id=None,
        pr_number=None,
        pr_url=None,
        was_created=False,
        base_branch=None,
        graphite_url=None,
        diff_file=None,
        plan_context=None,
        title=None,
        body=None,
        existing_pr_body="",
        graphite_is_authed=None,
        graphite_branch_tracked=None,
    )


def test_noop_when_impl_context_missing(tmp_path: Path) -> None:
    """No-op when .erk/impl-context/ does not exist on disk."""
    ctx = context_for_test(cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = cleanup_impl_for_submit(ctx, state)

    assert isinstance(result, SubmitState)
    assert result is state


def test_noop_when_not_tracked(tmp_path: Path) -> None:
    """No-op when .erk/impl-context/ exists on disk but is not git-tracked."""
    impl_dir = tmp_path / ".erk" / "impl-context"
    impl_dir.mkdir(parents=True)
    (impl_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")

    fake_git = FakeGit()
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = cleanup_impl_for_submit(ctx, state)

    assert isinstance(result, SubmitState)
    assert result is state
    assert impl_dir.exists()


def test_cleans_up_plan_branch(tmp_path: Path) -> None:
    """Plan branches (plnd/*) also get .erk/impl-context/ cleaned up on submit."""
    impl_dir = tmp_path / ".erk" / "impl-context"
    impl_dir.mkdir(parents=True)
    (impl_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")

    fake_git = FakeGit(
        tracked_paths={".erk/impl-context/plan.md"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, branch_name="plnd/my-plan-branch")

    result = cleanup_impl_for_submit(ctx, state)

    assert isinstance(result, SubmitState)
    assert not impl_dir.exists()
    assert len(fake_git.commits) == 1
    assert "impl-context" in fake_git.commits[0].message


def test_removes_tracked_impl_context(tmp_path: Path) -> None:
    """Removes .erk/impl-context/ when it exists and is git-tracked."""
    impl_dir = tmp_path / ".erk" / "impl-context"
    impl_dir.mkdir(parents=True)
    (impl_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (impl_dir / "ref.json").write_text("{}", encoding="utf-8")

    fake_git = FakeGit(
        tracked_paths={".erk/impl-context/plan.md", ".erk/impl-context/ref.json"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = cleanup_impl_for_submit(ctx, state)

    assert isinstance(result, SubmitState)
    assert not impl_dir.exists()
    assert len(fake_git.commits) == 1
    assert "impl-context" in fake_git.commits[0].message
