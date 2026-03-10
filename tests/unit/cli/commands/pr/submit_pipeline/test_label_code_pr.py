"""Unit tests for label_code_pr pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitState,
    label_code_pr,
)
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.test_utils.test_context import context_for_test


def _make_state(
    *,
    cwd: Path,
    repo_root: Path | None = None,
    pr_id: str | None = None,
    pr_number: int | None = None,
) -> SubmitState:
    return SubmitState(
        cwd=cwd,
        repo_root=repo_root if repo_root is not None else cwd,
        branch_name="feature",
        parent_branch="main",
        trunk_branch="main",
        use_graphite=True,
        force=False,
        debug=False,
        session_id="test-session",
        skip_description=False,
        quiet=False,
        pr_id=pr_id,
        pr_number=pr_number,
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


def test_labels_code_pr(tmp_path: Path) -> None:
    """Adds erk-pr label to a non-plan code PR."""
    fake_local_github = FakeLocalGitHub()
    ctx = context_for_test(github=fake_local_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, pr_number=42)

    result = label_code_pr(ctx, state)

    assert isinstance(result, SubmitState)
    assert (42, "erk-pr") in fake_local_github.added_labels


def test_skips_plan_prs(tmp_path: Path) -> None:
    """Skips labeling when the PR is linked to a plan."""
    fake_local_github = FakeLocalGitHub()
    ctx = context_for_test(github=fake_local_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, pr_id="123", pr_number=42)

    result = label_code_pr(ctx, state)

    assert isinstance(result, SubmitState)
    assert result is state
    assert fake_local_github.added_labels == []


def test_skips_when_no_pr_number(tmp_path: Path) -> None:
    """Skips labeling when there is no PR number."""
    fake_local_github = FakeLocalGitHub()
    ctx = context_for_test(github=fake_local_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path, pr_number=None)

    result = label_code_pr(ctx, state)

    assert isinstance(result, SubmitState)
    assert result is state
    assert fake_local_github.added_labels == []
