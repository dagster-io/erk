"""Unit tests for fetch_plan_context pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitState,
    fetch_plan_context,
)
from erk.core.context import context_for_test


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
    plan_id: str | None = None,
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
        skip_description=skip_description,
        quiet=False,
        plan_id=plan_id,
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
    ctx = context_for_test(cwd=tmp_path)
    state = _make_state(cwd=tmp_path, skip_description=True)

    result = fetch_plan_context(ctx, state)

    assert result is state
