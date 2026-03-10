"""Unit tests for capture_existing_pr_body pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitState,
    capture_existing_pr_body,
)
from erk_shared.gateway.github.types import PRDetails
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.test_utils.test_context import context_for_test

_PR_BODY_WITH_METADATA = (
    "<!-- erk:metadata-block:start -->\n"
    "schema_version: 2\n"
    "created_by: test\n"
    "<!-- erk:metadata-block:end -->\n\n---\n\n"
    "Plan content here"
)


def _make_state(
    *,
    cwd: Path,
    branch_name: str = "feature",
    existing_pr_body: str = "",
) -> SubmitState:
    return SubmitState(
        cwd=cwd,
        repo_root=cwd,
        branch_name=branch_name,
        parent_branch="main",
        trunk_branch="main",
        use_graphite=False,
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
        existing_pr_body=existing_pr_body,
        graphite_is_authed=None,
        graphite_branch_tracked=None,
    )


def _pr_with_metadata(*, number: int = 42, branch: str = "feature") -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Test PR",
        body=_PR_BODY_WITH_METADATA,
        state="OPEN",
        base_ref_name="main",
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=True,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )


def test_captures_full_body_from_existing_pr(tmp_path: Path) -> None:
    """Full PR body is captured from existing PR."""
    pr = _pr_with_metadata(number=42, branch="feature")
    fake_github = FakeLocalGitHub(
        prs_by_branch={"feature": pr},
    )
    ctx = context_for_test(github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = capture_existing_pr_body(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.existing_pr_body == pr.body


def test_no_pr_returns_state_unchanged(tmp_path: Path) -> None:
    """When no PR exists for the branch, state is returned unchanged."""
    fake_github = FakeLocalGitHub()
    ctx = context_for_test(github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = capture_existing_pr_body(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.existing_pr_body == ""


def test_pr_with_empty_body_returns_state_unchanged(tmp_path: Path) -> None:
    """When PR body is empty, state is returned unchanged."""
    pr = PRDetails(
        number=42,
        url="https://github.com/owner/repo/pull/42",
        title="Test PR",
        body="",
        state="OPEN",
        base_ref_name="main",
        head_ref_name="feature",
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )
    fake_github = FakeLocalGitHub(
        prs_by_branch={"feature": pr},
    )
    ctx = context_for_test(github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = capture_existing_pr_body(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.existing_pr_body == ""
