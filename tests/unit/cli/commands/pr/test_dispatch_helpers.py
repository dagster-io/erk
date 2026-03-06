"""Unit tests for dispatch_helpers.ensure_trunk_synced."""

from pathlib import Path

import pytest

from erk.cli.commands.pr.dispatch_helpers import ensure_trunk_synced
from erk_shared.context.testing import context_for_test
from erk_shared.context.types import RepoContext
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit

LOCAL_SHA = "aaa1111"
REMOTE_SHA = "bbb2222"


def _repo_context(tmp_path: Path) -> RepoContext:
    return RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=tmp_path / ".erk" / "repos" / "test-repo",
        worktrees_dir=tmp_path / ".erk" / "repos" / "test-repo" / "worktrees",
        pool_json_path=tmp_path / ".erk" / "repos" / "test-repo" / "pool.json",
    )


def test_already_synced_is_noop(tmp_path: Path) -> None:
    """When local and remote trunk have the same SHA, nothing happens."""
    git = FakeGit(
        current_branches={tmp_path: "feature/work"},
        trunk_branches={tmp_path: "master"},
        branch_heads={"master": LOCAL_SHA, "origin/master": LOCAL_SHA},
    )
    ctx = context_for_test(git=git, cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    ensure_trunk_synced(ctx, repo)

    # No refs updated when already synced
    assert len(git.updated_refs) == 0


def test_local_behind_remote_fast_forwards(tmp_path: Path) -> None:
    """When local trunk is behind remote, update_local_ref advances it."""
    git = FakeGit(
        current_branches={tmp_path: "feature/work"},
        trunk_branches={tmp_path: "master"},
        branch_heads={"master": LOCAL_SHA, "origin/master": REMOTE_SHA},
        merge_bases={("master", "origin/master"): LOCAL_SHA},
    )
    ctx = context_for_test(git=git, cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    ensure_trunk_synced(ctx, repo)

    assert len(git.updated_refs) == 1
    ref_update = git.updated_refs[0]
    assert ref_update[1] == "master"
    assert ref_update[2] == REMOTE_SHA


def test_local_ahead_of_remote_exits(tmp_path: Path) -> None:
    """When local trunk is ahead of remote, exits with error."""
    git = FakeGit(
        current_branches={tmp_path: "feature/work"},
        trunk_branches={tmp_path: "master"},
        branch_heads={"master": REMOTE_SHA, "origin/master": LOCAL_SHA},
        merge_bases={("master", "origin/master"): LOCAL_SHA},
    )
    ctx = context_for_test(git=git, cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    with pytest.raises(SystemExit):
        ensure_trunk_synced(ctx, repo)


def test_diverged_exits(tmp_path: Path) -> None:
    """When local trunk has diverged from remote, exits with error."""
    diverge_base = "ccc3333"
    git = FakeGit(
        current_branches={tmp_path: "feature/work"},
        trunk_branches={tmp_path: "master"},
        branch_heads={"master": LOCAL_SHA, "origin/master": REMOTE_SHA},
        merge_bases={("master", "origin/master"): diverge_base},
    )
    ctx = context_for_test(git=git, cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    with pytest.raises(SystemExit):
        ensure_trunk_synced(ctx, repo)


def test_trunk_checked_out_with_clean_worktree_uses_pull(tmp_path: Path) -> None:
    """When trunk is checked out in a clean worktree, uses pull_branch (not update_local_ref)."""
    git = FakeGit(
        current_branches={tmp_path: "master"},
        trunk_branches={tmp_path: "master"},
        branch_heads={"master": LOCAL_SHA, "origin/master": REMOTE_SHA},
        merge_bases={("master", "origin/master"): LOCAL_SHA},
        worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="master", is_root=True)]},
    )
    ctx = context_for_test(git=git, cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    ensure_trunk_synced(ctx, repo)

    # Should use pull_branch to update index + working tree, not update_local_ref
    assert len(git.updated_refs) == 0
    assert len(git.pulled_branches) == 1
    assert git.pulled_branches[0] == ("origin", "master", True)


def test_trunk_checked_out_with_dirty_worktree_exits(tmp_path: Path) -> None:
    """When trunk is checked out in a dirty worktree, exits with error."""
    git = FakeGit(
        current_branches={tmp_path: "master"},
        trunk_branches={tmp_path: "master"},
        branch_heads={"master": LOCAL_SHA, "origin/master": REMOTE_SHA},
        merge_bases={("master", "origin/master"): LOCAL_SHA},
        worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="master", is_root=True)]},
        file_statuses={tmp_path: ([], ["modified-file.py"], [])},
    )
    ctx = context_for_test(git=git, cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    with pytest.raises(SystemExit):
        ensure_trunk_synced(ctx, repo)

    # Should NOT have updated the ref
    assert len(git.updated_refs) == 0


def test_trunk_in_root_worktree_uses_pull_not_update_ref(tmp_path: Path) -> None:
    """When trunk is checked out in root worktree and cwd is a slot worktree, uses pull."""
    root_path = tmp_path / "root"
    slot_path = tmp_path / "slot"
    root_path.mkdir()
    slot_path.mkdir()

    git = FakeGit(
        current_branches={root_path: "master", slot_path: "feature/work"},
        trunk_branches={root_path: "master"},
        branch_heads={"master": LOCAL_SHA, "origin/master": REMOTE_SHA},
        merge_bases={("master", "origin/master"): LOCAL_SHA},
        worktrees={root_path: [
            WorktreeInfo(path=root_path, branch="master", is_root=True),
            WorktreeInfo(path=slot_path, branch="feature/work", is_root=False),
        ]},
    )
    ctx = context_for_test(git=git, cwd=slot_path, repo_root=root_path)
    repo = _repo_context(root_path)

    ensure_trunk_synced(ctx, repo)

    # Must use pull (not update_local_ref) since trunk is checked out in root worktree
    assert len(git.updated_refs) == 0
    assert len(git.pulled_branches) == 1
    assert git.pulled_branches[0] == ("origin", "master", True)


def test_does_not_require_trunk_checkout(tmp_path: Path) -> None:
    """Can sync trunk even when a different branch is checked out (no worktree with trunk)."""
    git = FakeGit(
        current_branches={tmp_path: "feature/work"},
        trunk_branches={tmp_path: "master"},
        branch_heads={"master": LOCAL_SHA, "origin/master": REMOTE_SHA},
        merge_bases={("master", "origin/master"): LOCAL_SHA},
        # No worktree has trunk checked out
        worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="feature/work", is_root=True)]},
    )
    ctx = context_for_test(git=git, cwd=tmp_path, repo_root=tmp_path)
    repo = _repo_context(tmp_path)

    ensure_trunk_synced(ctx, repo)

    assert len(git.updated_refs) == 1
    assert git.updated_refs[0][1] == "master"
    assert git.updated_refs[0][2] == REMOTE_SHA
