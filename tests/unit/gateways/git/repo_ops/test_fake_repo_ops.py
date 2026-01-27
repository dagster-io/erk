"""Tests for FakeGitRepoOps."""

import subprocess
from pathlib import Path

import pytest

from erk_shared.gateway.git.repo_ops.fake import FakeGitRepoOps


def test_get_repository_root_returns_configured_root() -> None:
    """Test that get_repository_root returns the configured root."""
    repo_root = Path("/repo")
    Path("/repo/subdir")

    fake = FakeGitRepoOps(repository_roots={repo_root: repo_root})

    result = fake.get_repository_root(repo_root)
    assert result == repo_root


def test_get_repository_root_walks_up_to_find_root() -> None:
    """Test that get_repository_root walks up parent directories."""
    repo_root = Path("/repo")
    cwd = Path("/repo/subdir/nested")

    fake = FakeGitRepoOps(repository_roots={repo_root: repo_root})

    result = fake.get_repository_root(cwd)
    assert result == repo_root


def test_get_repository_root_raises_when_not_in_repo() -> None:
    """Test that get_repository_root raises when not in a repository."""
    fake = FakeGitRepoOps(repository_roots={})

    with pytest.raises(subprocess.CalledProcessError):
        fake.get_repository_root(Path("/not/a/repo"))


def test_get_git_common_dir_returns_configured_dir() -> None:
    """Test that get_git_common_dir returns the configured directory."""
    cwd = Path("/repo")
    git_dir = Path("/repo/.git")

    fake = FakeGitRepoOps(git_common_dirs={cwd: git_dir})

    result = fake.get_git_common_dir(cwd)
    assert result == git_dir


def test_get_git_common_dir_returns_none_when_not_configured() -> None:
    """Test that get_git_common_dir returns None gracefully."""
    fake = FakeGitRepoOps(git_common_dirs={})

    result = fake.get_git_common_dir(Path("/not/a/repo"))
    assert result is None


def test_link_state_updates_internal_state() -> None:
    """Test that link_state method updates the fake's state."""
    fake = FakeGitRepoOps()

    repo_roots = {Path("/repo"): Path("/repo")}
    git_dirs = {Path("/repo"): Path("/repo/.git")}

    fake.link_state(repository_roots=repo_roots, git_common_dirs=git_dirs)

    assert fake.get_repository_root(Path("/repo")) == Path("/repo")
    assert fake.get_git_common_dir(Path("/repo")) == Path("/repo/.git")
