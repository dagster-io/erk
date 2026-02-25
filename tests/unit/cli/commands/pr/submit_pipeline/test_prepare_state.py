"""Unit tests for prepare_state pipeline step."""

import json
from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    SubmitState,
    prepare_state,
)
from erk.core.context import context_for_test
from erk_shared.gateway.git.fake import FakeGit


def _make_state(
    *,
    cwd: Path,
    repo_root: Path | None = None,
    branch_name: str = "",
    parent_branch: str = "",
    trunk_branch: str = "",
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
        skip_description=False,
        quiet=False,
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
        metadata_prefix="",
    )


def test_resolves_branch_and_trunk(tmp_path: Path) -> None:
    """Happy path: all discovery fields populated."""
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.branch_name == "feature-branch"
    assert result.trunk_branch == "main"
    assert result.repo_root == tmp_path
    # No Graphite parent => falls back to trunk
    assert result.parent_branch == "main"


def test_detached_head_returns_error(tmp_path: Path) -> None:
    """current_branch=None => SubmitError(error_type='no_branch')."""
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: None},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    assert isinstance(result, SubmitError)
    assert result.error_type == "no_branch"


def test_issue_linkage_mismatch_returns_error(tmp_path: Path) -> None:
    """Branch with P-prefix cannot extract issue number, no mismatch possible.

    Since extract_leading_issue_number() always returns None, P-prefix branches
    cannot provide an issue number. The test verifies issue_number comes from
    issue.json without any mismatch error.
    """
    # Create .impl/issue.json with issue number
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 99,
                "issue_url": "https://github.com/owner/repo/issues/99",
                "created_at": "2025-01-01T00:00:00+00:00",
                "synced_at": "2025-01-01T00:00:00+00:00",
            }
        )
    )

    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "P42-some-feature"},
        trunk_branches={tmp_path: "main"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    # No mismatch error since branch cannot provide issue number
    assert isinstance(result, SubmitState)
    assert result.issue_number == 99  # From issue.json


def test_auto_repair_creates_plan_ref_json(tmp_path: Path) -> None:
    """Branch with P-prefix cannot extract issue number, no auto-repair possible.

    Since extract_leading_issue_number() always returns None, P-prefix branches
    cannot provide an issue number for auto-repair. Without plan-ref.json,
    issue_number remains None.
    """
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "P42-some-feature"},
        trunk_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    assert isinstance(result, SubmitState)
    # No auto-repair since branch cannot provide issue number
    assert result.issue_number is None
    # Verify plan-ref.json was NOT created
    plan_ref_json = impl_dir / "plan-ref.json"
    assert not plan_ref_json.exists()


def test_no_issue_number_from_branch(tmp_path: Path) -> None:
    """Regular branch (no P-prefix) => issue_number=None."""
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.issue_number is None


def test_issue_from_impl_folder(tmp_path: Path) -> None:
    """.impl/issue.json present => issue_number populated."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    issue_json = impl_dir / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 55,
                "issue_url": "https://github.com/owner/repo/issues/55",
                "created_at": "2025-01-01T00:00:00+00:00",
                "synced_at": "2025-01-01T00:00:00+00:00",
            }
        )
    )

    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.issue_number == 55


def test_parent_falls_back_to_trunk(tmp_path: Path) -> None:
    """No Graphite parent => parent_branch == trunk_branch."""
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "master"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.parent_branch == "master"
    assert result.trunk_branch == "master"
