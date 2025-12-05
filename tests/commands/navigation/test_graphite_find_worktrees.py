"""Tests for find_worktrees_containing_branch function in graphite.py."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo, find_worktree_for_branch
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.real import RealGraphite

from erk.cli.graphite import find_worktrees_containing_branch
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
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

    ctx = ErkContext.for_test(
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
