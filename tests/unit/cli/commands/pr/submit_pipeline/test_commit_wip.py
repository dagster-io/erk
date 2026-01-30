"""Unit tests for commit_wip pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitState,
    commit_wip,
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


def test_commits_when_uncommitted_changes(tmp_path: Path) -> None:
    """add_all + commit called when there are uncommitted changes."""
    fake_git = FakeGit(
        file_statuses={tmp_path: ([], ["modified.py"], [])},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = commit_wip(ctx, state)

    assert isinstance(result, SubmitState)
    # Verify add_all and commit were called
    assert len(fake_git.commit.commits) == 1
    assert fake_git.commit.commits[0].message == "WIP: Prepare for PR submission"


def test_skips_when_clean(tmp_path: Path) -> None:
    """No commit calls when working directory is clean."""
    fake_git = FakeGit()
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = commit_wip(ctx, state)

    assert isinstance(result, SubmitState)
    assert len(fake_git.commit.commits) == 0
