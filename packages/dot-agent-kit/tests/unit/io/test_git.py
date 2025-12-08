"""Tests for git utilities."""

import subprocess
from pathlib import Path

from dot_agent_kit.io.git import find_git_root, resolve_project_dir


def test_find_git_root_in_git_repo(tmp_path: Path) -> None:
    """Test find_git_root returns root when in a git repo."""
    # Create a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    result = find_git_root(tmp_path)

    assert result == tmp_path


def test_find_git_root_from_subdirectory(tmp_path: Path) -> None:
    """Test find_git_root returns root when called from a subdirectory."""
    # Create a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    # Create a subdirectory
    subdir = tmp_path / "python_modules" / "my_module"
    subdir.mkdir(parents=True)

    result = find_git_root(subdir)

    assert result == tmp_path


def test_find_git_root_not_in_git_repo(tmp_path: Path) -> None:
    """Test find_git_root returns None when not in a git repo."""
    result = find_git_root(tmp_path)

    assert result is None


def test_resolve_project_dir_in_git_repo(tmp_path: Path) -> None:
    """Test resolve_project_dir returns git root when in a repo."""
    # Create a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    result = resolve_project_dir(tmp_path)

    assert result == tmp_path


def test_resolve_project_dir_from_subdirectory(tmp_path: Path) -> None:
    """Test resolve_project_dir returns git root when called from subdirectory."""
    # Create a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    # Create a subdirectory
    subdir = tmp_path / "python_modules" / "dagster_open_platform"
    subdir.mkdir(parents=True)

    result = resolve_project_dir(subdir)

    assert result == tmp_path


def test_resolve_project_dir_not_in_git_repo(tmp_path: Path) -> None:
    """Test resolve_project_dir returns cwd when not in a git repo."""
    result = resolve_project_dir(tmp_path)

    assert result == tmp_path


def test_resolve_project_dir_deep_nesting(tmp_path: Path) -> None:
    """Test resolve_project_dir works with deeply nested subdirectories."""
    # Create a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    # Create deeply nested subdirectory
    deep_subdir = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep_subdir.mkdir(parents=True)

    result = resolve_project_dir(deep_subdir)

    assert result == tmp_path
