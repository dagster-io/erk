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
    """Branch P42-x + issue.json with issue 99 => error."""
    # Create .impl/issue.json with mismatched issue number
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

    assert isinstance(result, SubmitError)
    assert result.error_type == "issue_linkage_mismatch"


def test_auto_repair_creates_issue_json(tmp_path: Path) -> None:
    """Branch P42-x + .impl/ exists + no issue.json => creates file."""
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
    assert result.issue_number == 42
    # Verify issue.json was created
    issue_json = impl_dir / "issue.json"
    assert issue_json.exists()
    data = json.loads(issue_json.read_text())
    assert data["issue_number"] == 42


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
