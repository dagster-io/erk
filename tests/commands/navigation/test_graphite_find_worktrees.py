"""Tests for find_worktrees_containing_branch and Graphite.find_ancestor_worktree."""

from pathlib import Path

import pytest

from erk.cli.graphite import find_worktrees_containing_branch
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.graphite.real import RealGraphite
from erk_shared.git.abc import WorktreeInfo, find_worktree_for_branch
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.fakes.shell import FakeShell
from tests.test_utils.graphite_helpers import setup_graphite_stack


def test_find_worktrees_containing_branch_no_match(tmp_path: Path) -> None:
    """Test searching for a branch that doesn't exist in any stack."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    work_dir = tmp_path / "erks" / "repo"
    work_dir.mkdir(parents=True)

    # Set up stack: main -> feature-1
    setup_graphite_stack(
        git_dir,
        {
            "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
            "feature-1": {"parent": "main", "children": []},
        },
    )

    wt1_path = work_dir / "feature-1-wt"

    worktrees = [
        WorktreeInfo(path=repo_root, branch="main"),
        WorktreeInfo(path=wt1_path, branch="feature-1"),
    ]

    git_ops = FakeGit(
        worktrees={repo_root: worktrees},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: git_dir},
    )

    graphite_ops = RealGraphite()

    ctx = context_for_test(
        git=git_ops,
        global_config=GlobalConfig.test(
            Path("/fake/erks"), use_graphite=False, shell_setup_complete=False
        ),
        github=FakeGitHub(),
        graphite=graphite_ops,
        shell=FakeShell(),
        cwd=tmp_path,
        dry_run=False,
    )

    # Search for a branch that doesn't exist in any stack
    matching = find_worktrees_containing_branch(ctx, repo_root, worktrees, "nonexistent-branch")

    # Should return empty list
    assert len(matching) == 0
    assert matching == []


def test_find_worktree_for_branch_simple_match(tmp_path: Path) -> None:
    """Test finding worktree path for a branch that exists."""
    work_dir = tmp_path / "erks" / "repo"
    work_dir.mkdir(parents=True)

    feature_path = work_dir / "feature-work"
    main_path = tmp_path / "repo"

    worktrees = [
        WorktreeInfo(path=main_path, branch="main"),
        WorktreeInfo(path=feature_path, branch="feature-1"),
    ]

    result = find_worktree_for_branch(worktrees, "feature-1")
    assert result == feature_path


def test_find_worktree_for_branch_no_match(tmp_path: Path) -> None:
    """Test finding worktree for a branch that doesn't exist returns None."""
    work_dir = tmp_path / "erks" / "repo"
    work_dir.mkdir(parents=True)

    worktrees = [
        WorktreeInfo(path=work_dir / "feature-1", branch="feature-1"),
        WorktreeInfo(path=work_dir / "feature-2", branch="feature-2"),
    ]

    result = find_worktree_for_branch(worktrees, "nonexistent-branch")
    assert result is None


def test_find_worktree_for_branch_empty_list() -> None:
    """Test finding worktree in empty worktree list returns None."""
    worktrees: list[WorktreeInfo] = []

    result = find_worktree_for_branch(worktrees, "any-branch")
    assert result is None


def test_find_worktree_for_branch_mismatched_names(tmp_path: Path) -> None:
    """Test the key scenario: branch name differs from worktree directory name.

    This is the regression test for the bug - the fix allows branch-to-worktree
    resolution even when directory names don't match branch names.
    """
    work_dir = tmp_path / "erks" / "repo"
    work_dir.mkdir(parents=True)

    # Branch names have slashes, worktree paths use different names
    worktrees = [
        WorktreeInfo(path=tmp_path / "repo", branch="main"),
        WorktreeInfo(path=work_dir / "auth-implementation", branch="feature/auth"),
        WorktreeInfo(path=work_dir / "api-refactor", branch="feature/api-v2"),
    ]

    # Should find the worktree by branch name, not by directory name
    auth_result = find_worktree_for_branch(worktrees, "feature/auth")
    assert auth_result == work_dir / "auth-implementation"

    api_result = find_worktree_for_branch(worktrees, "feature/api-v2")
    assert api_result == work_dir / "api-refactor"


def test_find_worktree_for_branch_detached_head(tmp_path: Path) -> None:
    """Test that worktrees with detached HEAD (branch=None) are skipped."""
    work_dir = tmp_path / "erks" / "repo"
    work_dir.mkdir(parents=True)

    worktrees = [
        WorktreeInfo(path=work_dir / "main", branch="main"),
        WorktreeInfo(path=work_dir / "detached", branch=None),  # Detached HEAD
        WorktreeInfo(path=work_dir / "feature", branch="feature-1"),
    ]

    # Should find feature-1
    result = find_worktree_for_branch(worktrees, "feature-1")
    assert result == work_dir / "feature"

    # Should not match None (detached HEAD)
    none_result = find_worktree_for_branch(worktrees, "None")
    assert none_result is None


def test_find_ancestor_worktree_finds_parent(tmp_path: Path) -> None:
    """Test finding ancestor worktree when parent branch has one."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    work_dir = tmp_path / "erks" / "repo"
    work_dir.mkdir(parents=True)

    # Set up stack: main -> feat-1 -> feat-2
    # feat-2 has no worktree, should find feat-1's worktree
    setup_graphite_stack(
        git_dir,
        {
            "main": {"parent": None, "children": ["feat-1"], "is_trunk": True},
            "feat-1": {"parent": "main", "children": ["feat-2"]},
            "feat-2": {"parent": "feat-1", "children": []},
        },
    )

    feat1_path = work_dir / "feat-1"
    worktrees = [
        WorktreeInfo(path=repo_root, branch="main", is_root=True),
        WorktreeInfo(path=feat1_path, branch="feat-1", is_root=False),
        # feat-2 has NO worktree
    ]

    git_ops = FakeGit(
        worktrees={repo_root: worktrees},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: git_dir},
    )

    graphite_ops = RealGraphite()

    # feat-2 has no worktree, should find feat-1's worktree (its parent)
    result = graphite_ops.find_ancestor_worktree(git_ops, repo_root, "feat-2")
    assert result is not None
    assert result.branch == "feat-1"
    assert result.path == feat1_path


def test_find_ancestor_worktree_finds_grandparent(tmp_path: Path) -> None:
    """Test finding ancestor worktree when grandparent has one but parent doesn't."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    work_dir = tmp_path / "erks" / "repo"
    work_dir.mkdir(parents=True)

    # Set up stack: main -> feat-1 -> feat-2 -> feat-3
    # Only main has a worktree - feat-3 should find main's worktree
    setup_graphite_stack(
        git_dir,
        {
            "main": {"parent": None, "children": ["feat-1"], "is_trunk": True},
            "feat-1": {"parent": "main", "children": ["feat-2"]},
            "feat-2": {"parent": "feat-1", "children": ["feat-3"]},
            "feat-3": {"parent": "feat-2", "children": []},
        },
    )

    worktrees = [
        WorktreeInfo(path=repo_root, branch="main", is_root=True),
        # feat-1, feat-2, feat-3 have NO worktrees
    ]

    git_ops = FakeGit(
        worktrees={repo_root: worktrees},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: git_dir},
    )

    graphite_ops = RealGraphite()

    # feat-3 has no worktree and neither do feat-2/feat-1, should find main's worktree
    result = graphite_ops.find_ancestor_worktree(git_ops, repo_root, "feat-3")
    assert result is not None
    assert result.branch == "main"
    assert result.path == repo_root


def test_find_ancestor_worktree_no_ancestor_with_worktree(tmp_path: Path) -> None:
    """Test returns None when no ancestor has a worktree."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()

    # Set up stack: main -> feat-1
    # But we configure empty worktree list (simulating no worktrees)
    setup_graphite_stack(
        git_dir,
        {
            "main": {"parent": None, "children": ["feat-1"], "is_trunk": True},
            "feat-1": {"parent": "main", "children": []},
        },
    )

    git_ops = FakeGit(
        worktrees={repo_root: []},  # No worktrees at all
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: git_dir},
    )

    graphite_ops = RealGraphite()

    result = graphite_ops.find_ancestor_worktree(git_ops, repo_root, "feat-1")
    assert result is None


def test_find_ancestor_worktree_trunk_branch(tmp_path: Path) -> None:
    """Test returns None for trunk branch (no parent)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()

    setup_graphite_stack(
        git_dir,
        {
            "main": {"parent": None, "children": [], "is_trunk": True},
        },
    )

    worktrees = [
        WorktreeInfo(path=repo_root, branch="main", is_root=True),
    ]

    git_ops = FakeGit(
        worktrees={repo_root: worktrees},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: git_dir},
    )

    graphite_ops = RealGraphite()

    # main is trunk with no parent, should return None
    result = graphite_ops.find_ancestor_worktree(git_ops, repo_root, "main")
    assert result is None


def test_find_ancestor_worktree_untracked_branch(tmp_path: Path) -> None:
    """Test raises ValueError for branch not tracked by Graphite."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()

    # Set up stack with only main - untracked-branch is NOT in Graphite
    setup_graphite_stack(
        git_dir,
        {
            "main": {"parent": None, "children": [], "is_trunk": True},
        },
    )

    worktrees = [
        WorktreeInfo(path=repo_root, branch="main", is_root=True),
    ]

    git_ops = FakeGit(
        worktrees={repo_root: worktrees},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: git_dir},
    )

    graphite_ops = RealGraphite()

    # untracked-branch is not in Graphite, should raise ValueError (caller bug)
    with pytest.raises(ValueError, match="not tracked by Graphite"):
        graphite_ops.find_ancestor_worktree(git_ops, repo_root, "untracked-branch")
