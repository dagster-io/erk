"""Unit tests for prepare_state pipeline step."""

import json
from pathlib import Path

from erk.cli.commands.pr.submit_pipeline import (
    SubmitError,
    SubmitState,
    prepare_state,
)
from erk_shared.impl_folder import get_impl_dir
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.test_context import context_for_test

BRANCH = "test/branch"
"""Test branch name used across tests."""


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
        skip_description=False,
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

    P-prefix branches cannot provide an issue number. The test verifies plan_id
    comes from ref.json without any mismatch error.
    """
    # Create branch-scoped impl dir with ref.json
    impl_dir = get_impl_dir(tmp_path, branch_name="P42-some-feature")
    impl_dir.mkdir(parents=True)
    ref_json = impl_dir / "ref.json"
    ref_json.write_text(
        json.dumps(
            {
                "provider": "github",
                "plan_id": "99",
                "url": "https://github.com/owner/repo/issues/99",
                "created_at": "2025-01-01T00:00:00+00:00",
                "synced_at": "2025-01-01T00:00:00+00:00",
            }
        )
    )

    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "P42-some-feature"},
        trunk_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    # No mismatch error since branch cannot provide issue number
    assert isinstance(result, SubmitState)
    assert result.plan_id == "99"  # From ref.json


def test_auto_repair_creates_plan_ref_json(tmp_path: Path) -> None:
    """Branch with P-prefix cannot extract issue number, no auto-repair possible.

    P-prefix branches cannot provide an issue number for auto-repair. Without
    plan-ref.json, plan_id remains None.
    """
    impl_dir = get_impl_dir(tmp_path, branch_name="P42-some-feature")
    impl_dir.mkdir(parents=True)

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
    assert result.plan_id is None
    # Verify ref.json was NOT created
    plan_ref_json = impl_dir / "ref.json"
    assert not plan_ref_json.exists()


def test_no_plan_id_from_branch(tmp_path: Path) -> None:
    """Regular branch (no P-prefix) => plan_id=None."""
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.plan_id is None


def test_plan_id_from_impl_folder(tmp_path: Path) -> None:
    """Branch-scoped impl dir with ref.json present => plan_id populated."""
    impl_dir = get_impl_dir(tmp_path, branch_name="feature-branch")
    impl_dir.mkdir(parents=True)
    ref_json = impl_dir / "ref.json"
    ref_json.write_text(
        json.dumps(
            {
                "provider": "github",
                "plan_id": "55",
                "url": "https://github.com/owner/repo/issues/55",
                "created_at": "2025-01-01T00:00:00+00:00",
                "synced_at": "2025-01-01T00:00:00+00:00",
            }
        )
    )

    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
        remote_urls={(tmp_path, "origin"): "git@github.com:owner/repo.git"},
    )
    ctx = context_for_test(git=fake_git, cwd=tmp_path)
    state = _make_state(cwd=tmp_path)

    result = prepare_state(ctx, state)

    assert isinstance(result, SubmitState)
    assert result.plan_id == "55"


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
