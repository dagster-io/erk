"""Tests for navigation helper completion functions."""

from pathlib import Path
from unittest.mock import Mock

import click
from erk_shared.git.fake import FakeGit

from erk.cli.commands.completions import complete_branch_names, complete_plan_files
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext


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

    global_config = GlobalConfig(
        erk_root=erk_root, use_graphite=False, shell_setup_complete=False, show_pr_info=False
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

    global_config = GlobalConfig(
        erk_root=erk_root, use_graphite=False, shell_setup_complete=False, show_pr_info=False
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

    global_config = GlobalConfig(
        erk_root=erk_root, use_graphite=False, shell_setup_complete=False, show_pr_info=False
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

    global_config = GlobalConfig(
        erk_root=erk_root, use_graphite=False, shell_setup_complete=False, show_pr_info=False
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

    global_config = GlobalConfig(
        erk_root=erk_root, use_graphite=False, shell_setup_complete=False, show_pr_info=False
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

    global_config = GlobalConfig(
        erk_root=erk_root, use_graphite=False, shell_setup_complete=False, show_pr_info=False
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

    global_config = GlobalConfig(
        erk_root=erk_root, use_graphite=False, shell_setup_complete=False, show_pr_info=False
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

    global_config = GlobalConfig(
        erk_root=erk_root, use_graphite=False, shell_setup_complete=False, show_pr_info=False
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
