"""Tests for navigation helper functions."""

import os
from pathlib import Path
from unittest.mock import Mock

import click
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit

from erk.cli.commands.completions import complete_branch_names, complete_plan_files
from erk.cli.commands.navigation_helpers import delete_branch_and_worktree
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext


def make_test_repo_context(
    repo_root: Path,
    *,
    main_repo_root: Path | None = None,
    erk_root: Path | None = None,
) -> RepoContext:
    """Create a RepoContext for testing with sensible defaults.

    Args:
        repo_root: The repository root path (also used as main_repo_root if not specified)
        main_repo_root: The main repo root (defaults to repo_root)
        erk_root: The erk root directory (defaults to repo_root.parent / "erks")
    """
    main_repo = main_repo_root if main_repo_root is not None else repo_root
    erk = erk_root if erk_root is not None else repo_root.parent / "erks"
    return RepoContext(
        root=repo_root,
        main_repo_root=main_repo,
        repo_name="test-repo",
        repo_dir=erk / "repos" / "test-repo",
        worktrees_dir=erk / "repos" / "test-repo" / "worktrees",
    )


def test_complete_branch_names_local_branches(tmp_path: Path) -> None:
    """Test completion returns local branch names."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    git = FakeGit(
        local_branches={repo_root: ["main", "feature-a", "feature-b"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx_obj = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)

    # Create mock Click context
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = ctx_obj
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    result = complete_branch_names(mock_ctx, None, "")

    # Assert
    assert sorted(result) == ["feature-a", "feature-b", "main"]


def test_complete_branch_names_remote_branches_strip_prefix(tmp_path: Path) -> None:
    """Test completion strips remote prefixes from remote branch names."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    git = FakeGit(
        local_branches={repo_root: ["main"]},
        remote_branches={repo_root: ["origin/feature-c", "upstream/feature-d"]},
        git_common_dirs={repo_root: git_dir},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx_obj = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)

    # Create mock Click context
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = ctx_obj
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    result = complete_branch_names(mock_ctx, None, "")

    # Assert
    assert sorted(result) == ["feature-c", "feature-d", "main"]


def test_complete_branch_names_deduplication(tmp_path: Path) -> None:
    """Test completion deduplicates branches that exist both locally and remotely."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    git = FakeGit(
        local_branches={repo_root: ["main", "feature-a"]},
        remote_branches={repo_root: ["origin/main", "origin/feature-a", "origin/feature-b"]},
        git_common_dirs={repo_root: git_dir},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx_obj = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)

    # Create mock Click context
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = ctx_obj
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    result = complete_branch_names(mock_ctx, None, "")

    # Assert
    # Should see each branch only once, not duplicated
    assert sorted(result) == ["feature-a", "feature-b", "main"]


def test_complete_branch_names_filters_by_prefix(tmp_path: Path) -> None:
    """Test completion filters branches by incomplete prefix."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    git = FakeGit(
        local_branches={repo_root: ["main", "feature-a", "feature-b", "bugfix-1"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx_obj = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)

    # Create mock Click context
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = ctx_obj
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    result = complete_branch_names(mock_ctx, None, "feat")

    # Assert
    assert sorted(result) == ["feature-a", "feature-b"]


def test_complete_branch_names_handles_uninitialized_context(tmp_path: Path) -> None:
    """Test completion handles ctx.find_root().obj being None gracefully."""
    # Arrange
    # Create mock Click context with None obj (uninitialized)
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = None
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    # This should not crash - it creates a default context internally
    result = complete_branch_names(mock_ctx, None, "")

    # Assert
    # Result may be empty or contain branches from actual git repo if in one,
    # but the important thing is it doesn't crash
    assert isinstance(result, list)


def test_complete_branch_names_error_handling_returns_empty_list(tmp_path: Path) -> None:
    """Test completion returns empty list on error for graceful degradation."""
    # Arrange
    # Create mock Click context that will cause an exception
    mock_ctx = Mock(spec=click.Context)
    mock_ctx.find_root.side_effect = Exception("Simulated error")

    # Act
    result = complete_branch_names(mock_ctx, None, "")

    # Assert
    # Should return empty list, not raise exception
    assert result == []


def test_complete_plan_files_finds_markdown_files(tmp_path: Path) -> None:
    """Test completion finds .md files in current directory."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    # Create test .md files
    (repo_root / "feature-plan.md").touch()
    (repo_root / "bugfix-plan.md").touch()
    (repo_root / "readme.md").touch()

    git = FakeGit(
        local_branches={repo_root: ["main"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx_obj = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)

    # Create mock Click context
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = ctx_obj
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    result = complete_plan_files(mock_ctx, None, "")

    # Assert
    assert sorted(result) == ["bugfix-plan.md", "feature-plan.md", "readme.md"]


def test_complete_plan_files_no_markdown_files(tmp_path: Path) -> None:
    """Test completion returns empty list when no .md files exist."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    # Create non-markdown files
    (repo_root / "readme.txt").touch()
    (repo_root / "notes.pdf").touch()

    git = FakeGit(
        local_branches={repo_root: ["main"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx_obj = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)

    # Create mock Click context
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = ctx_obj
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    result = complete_plan_files(mock_ctx, None, "")

    # Assert
    assert result == []


def test_complete_plan_files_filters_by_prefix(tmp_path: Path) -> None:
    """Test completion filters by incomplete prefix."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    # Create test .md files
    (repo_root / "feature-plan.md").touch()
    (repo_root / "fix-plan.md").touch()
    (repo_root / "readme.md").touch()

    git = FakeGit(
        local_branches={repo_root: ["main"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx_obj = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)

    # Create mock Click context
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = ctx_obj
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    result = complete_plan_files(mock_ctx, None, "fea")

    # Assert
    assert result == ["feature-plan.md"]


def test_complete_plan_files_handles_uninitialized_context(tmp_path: Path) -> None:
    """Test completion handles ctx.find_root().obj being None gracefully."""
    # Arrange
    # Create mock Click context with None obj (uninitialized)
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = None
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    # This should not crash - it creates a default context internally
    result = complete_plan_files(mock_ctx, None, "")

    # Assert
    # Result may be empty or contain files if in a directory with .md files,
    # but the important thing is it doesn't crash
    assert isinstance(result, list)


def test_complete_plan_files_error_handling_returns_empty_list(tmp_path: Path) -> None:
    """Test completion returns empty list on error for graceful degradation."""
    # Arrange
    # Create mock Click context that will cause an exception
    mock_ctx = Mock(spec=click.Context)
    mock_ctx.find_root.side_effect = Exception("Simulated error")

    # Act
    result = complete_plan_files(mock_ctx, None, "")

    # Assert
    # Should return empty list, not raise exception
    assert result == []


def test_complete_plan_files_returns_sorted_results(tmp_path: Path) -> None:
    """Test completion returns results in sorted order."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    # Create test .md files in non-alphabetical order
    (repo_root / "z-plan.md").touch()
    (repo_root / "a-plan.md").touch()
    (repo_root / "m-plan.md").touch()

    git = FakeGit(
        local_branches={repo_root: ["main"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx_obj = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)

    # Create mock Click context
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = ctx_obj
    mock_ctx.find_root.return_value = mock_root_ctx

    # Act
    result = complete_plan_files(mock_ctx, None, "")

    # Assert
    assert result == ["a-plan.md", "m-plan.md", "z-plan.md"]


def test_delete_branch_and_worktree_escapes_cwd_when_inside(tmp_path: Path) -> None:
    """Test that delete_branch_and_worktree changes CWD before deletion when inside worktree."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()
    worktree_path = tmp_path / "worktrees" / "feature"
    worktree_path.mkdir(parents=True)

    git = FakeGit(
        local_branches={repo_root: ["main", "feature"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
        worktrees={repo_root: [WorktreeInfo(path=worktree_path, branch="feature")]},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)
    repo = make_test_repo_context(repo_root, erk_root=erk_root)

    # Change to the worktree directory (simulating being inside it)
    original_cwd = Path.cwd()
    os.chdir(worktree_path)

    try:
        # Act
        delete_branch_and_worktree(ctx, repo, "feature", worktree_path)

        # Assert: CWD should have changed to repo_root (main_repo_root)
        assert Path.cwd() == repo_root

        # Assert: Worktree removal was called
        assert worktree_path in git.removed_worktrees

        # Assert: Branch was deleted
        assert "feature" in git.deleted_branches
    finally:
        # Restore original CWD for test cleanup
        os.chdir(original_cwd)


def test_delete_branch_and_worktree_no_escape_when_outside(tmp_path: Path) -> None:
    """Test that delete_branch_and_worktree does not change CWD when outside worktree."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()
    worktree_path = tmp_path / "worktrees" / "feature"
    worktree_path.mkdir(parents=True)

    git = FakeGit(
        local_branches={repo_root: ["main", "feature"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
        worktrees={repo_root: [WorktreeInfo(path=worktree_path, branch="feature")]},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)
    repo = make_test_repo_context(repo_root, erk_root=erk_root)

    # Stay at repo_root (not inside worktree)
    original_cwd = Path.cwd()
    os.chdir(repo_root)

    try:
        # Act
        delete_branch_and_worktree(ctx, repo, "feature", worktree_path)

        # Assert: CWD should still be repo_root (unchanged)
        assert Path.cwd() == repo_root

        # Assert: Worktree removal was called
        assert worktree_path in git.removed_worktrees

        # Assert: Branch was deleted
        assert "feature" in git.deleted_branches
    finally:
        # Restore original CWD for test cleanup
        os.chdir(original_cwd)


def test_delete_branch_and_worktree_escapes_via_symlink(tmp_path: Path) -> None:
    """Test that delete_branch_and_worktree escapes CWD when worktree_path is accessed via symlink.

    This tests the fix for the bug where Path.cwd() returns a resolved path,
    but worktree_path might be a symlink. Without resolving both paths,
    the equality check fails even when they refer to the same directory.
    """
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()

    # Create the actual worktree directory
    worktrees_dir = tmp_path / "worktrees"
    worktrees_dir.mkdir()
    actual_worktree_path = worktrees_dir / "feature"
    actual_worktree_path.mkdir()

    # Create a symlink to the worktrees directory (common in some setups)
    symlink_worktrees = tmp_path / "wt-link"
    symlink_worktrees.symlink_to(worktrees_dir)
    symlinked_worktree_path = symlink_worktrees / "feature"

    git = FakeGit(
        local_branches={repo_root: ["main", "feature"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
        worktrees={repo_root: [WorktreeInfo(path=actual_worktree_path, branch="feature")]},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)
    repo = make_test_repo_context(repo_root, erk_root=erk_root)

    # Change to the ACTUAL worktree directory (resolved path)
    original_cwd = Path.cwd()
    os.chdir(actual_worktree_path)

    try:
        # Act: Pass the SYMLINKED path (unresolved) - this is the bug scenario
        # Before fix: symlinked_worktree_path != Path.cwd() because one is resolved
        # After fix: both are resolved, so they're equal
        delete_branch_and_worktree(ctx, repo, "feature", symlinked_worktree_path)

        # Assert: CWD should have changed to repo_root (escaped the worktree)
        # Before fix: this would FAIL because the paths didn't compare equal,
        # so os.chdir(repo_root) was never called
        assert Path.cwd() == repo_root

        # Assert: Worktree removal was called (with the symlinked path we passed)
        assert symlinked_worktree_path in git.removed_worktrees

        # Assert: Branch was deleted
        assert "feature" in git.deleted_branches
    finally:
        # Restore original CWD for test cleanup
        os.chdir(original_cwd)


def test_delete_branch_and_worktree_uses_main_repo_root(tmp_path: Path) -> None:
    """Regression test: function uses main_repo_root for safe directory escape.

    Bug: When repo.root (= worktree path) was used for directory escape, the function
    would delete the worktree, then fail when gt delete tried to run with
    cwd pointing to the deleted directory.

    Fix: The function now uses repo.main_repo_root (passed via RepoContext) to ensure
    gt delete runs from a directory that still exists after worktree removal.

    This test verifies the function escapes to main_repo_root (not repo.root) when
    running from inside a worktree.
    """
    # Arrange
    main_repo = tmp_path / "main-repo"
    main_repo.mkdir()
    git_dir = main_repo / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()
    worktree_path = tmp_path / "worktrees" / "feature"
    worktree_path.mkdir(parents=True)

    git = FakeGit(
        local_branches={main_repo: ["main", "feature"]},
        remote_branches={main_repo: []},
        git_common_dirs={main_repo: git_dir},
        worktrees={main_repo: [WorktreeInfo(path=worktree_path, branch="feature")]},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx = ErkContext.for_test(git=git, cwd=main_repo, global_config=global_config)

    # Simulate running from worktree: repo.root == worktree_path, but main_repo_root is different
    repo = make_test_repo_context(
        worktree_path,  # When in worktree, repo.root == worktree path
        main_repo_root=main_repo,  # But main_repo_root is the actual repo
        erk_root=erk_root,
    )

    # Change to the worktree directory (simulating being inside it)
    original_cwd = Path.cwd()
    os.chdir(worktree_path)

    try:
        # Act: Function should use main_repo_root for escape, not repo.root
        delete_branch_and_worktree(ctx, repo, "feature", worktree_path)

        # Assert: CWD should have changed to main_repo (not worktree_path)
        # Before fix: would escape to repo.root which == worktree_path (deleted!)
        # After fix: escapes to main_repo_root which still exists
        assert Path.cwd() == main_repo

        # Assert: Operations completed successfully
        assert "feature" in git.deleted_branches
        assert worktree_path in git.removed_worktrees
    finally:
        # Restore original CWD for test cleanup
        os.chdir(original_cwd)


def test_delete_branch_and_worktree_escapes_from_subdirectory(tmp_path: Path) -> None:
    """Test that delete_branch_and_worktree changes CWD when inside a subdirectory of worktree."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()
    erk_root = tmp_path / "erks"
    erk_root.mkdir()
    worktree_path = tmp_path / "worktrees" / "feature"
    worktree_path.mkdir(parents=True)
    subdir = worktree_path / "src" / "deep"
    subdir.mkdir(parents=True)

    git = FakeGit(
        local_branches={repo_root: ["main", "feature"]},
        remote_branches={repo_root: []},
        git_common_dirs={repo_root: git_dir},
        worktrees={repo_root: [WorktreeInfo(path=worktree_path, branch="feature")]},
    )

    global_config = GlobalConfig.test(
        erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=False,
    )

    ctx = ErkContext.for_test(git=git, cwd=repo_root, global_config=global_config)
    repo = make_test_repo_context(repo_root, erk_root=erk_root)

    # Change to a subdirectory inside the worktree
    original_cwd = Path.cwd()
    os.chdir(subdir)

    try:
        # Act
        delete_branch_and_worktree(ctx, repo, "feature", worktree_path)

        # Assert: CWD should have changed to repo_root
        assert Path.cwd() == repo_root

        # Assert: Worktree removal was called
        assert worktree_path in git.removed_worktrees

        # Assert: Branch was deleted
        assert "feature" in git.deleted_branches
    finally:
        # Restore original CWD for test cleanup
        os.chdir(original_cwd)
