"""Unit tests for capture_metadata_prefix pipeline step."""

from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitState,
    capture_metadata_prefix,
)
from erk.core.context import context_for_test
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails

_METADATA_BLOCK = (
    "<!-- erk:metadata-block:start -->\n"
    "schema_version: 2\n"
    "created_by: test\n"
    "<!-- erk:metadata-block:end -->"
)

_SEPARATOR = "\n\n---\n\n"


def _make_state(
    *,
    cwd: Path,
    branch_name: str = "feature",
    metadata_prefix: str = "",
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
        issue_number=None,
        pr_number=None,
        pr_url=None,
        was_created=False,
        base_branch=None,
        graphite_url=None,
        diff_file=None,
        plan_context=None,
        title=None,
        body=None,
        metadata_prefix=metadata_prefix,
    )


def _pr_with_metadata(*, number: int = 42, branch: str = "feature") -> PRDetails:
    body = _METADATA_BLOCK + _SEPARATOR + "Plan content here"
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Test PR",
        body=body,
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


def test_captures_metadata_from_existing_pr(tmp_path: Path) -> None:
    """Metadata prefix is captured from PR body containing a metadata block."""
    pr = _pr_with_metadata(number=42, branch="feature")
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
    )
    ctx = context_for_test(github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = capture_metadata_prefix(ctx, state)

    assert isinstance(result, SubmitState)
    assert "<!-- erk:metadata-block:start -->" in result.metadata_prefix
    assert result.metadata_prefix.endswith(_SEPARATOR)


def test_no_pr_returns_state_unchanged(tmp_path: Path) -> None:
    """When no PR exists for the branch, state is returned unchanged."""
    fake_github = FakeGitHub()
    ctx = context_for_test(github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = capture_metadata_prefix(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.metadata_prefix == ""


def test_pr_without_metadata_returns_state_unchanged(tmp_path: Path) -> None:
    """When PR body has no metadata block, state is returned unchanged."""
    pr = PRDetails(
        number=42,
        url="https://github.com/owner/repo/pull/42",
        title="Test PR",
        body="Just a plain PR body with no metadata",
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
    fake_github = FakeGitHub(
        prs_by_branch={"feature": pr},
    )
    ctx = context_for_test(github=fake_github, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = capture_metadata_prefix(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.metadata_prefix == ""
