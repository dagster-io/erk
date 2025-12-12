"""Fixtures and helpers for integration tests.

This module provides fixtures that configure real git operations for integration testing.
"""

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit


class GitSetup(NamedTuple):
    """Result of git operations setup fixture for integration testing.

    Attributes:
        git: RealGit instance for integration testing
        repo: Path to the real repository root
    """

    git: Git
    repo: Path


class GitWithWorktrees(NamedTuple):
    """Result of git operations setup with multiple worktrees for integration testing.

    Attributes:
        git: RealGit instance for integration testing
        repo: Path to the real repository root
        worktrees: List of real worktree paths (wt1, wt2, etc.)
    """

    git: Git
    repo: Path
    worktrees: list[Path]


class GitWithDetached(NamedTuple):
    """Result of git operations setup with detached HEAD worktree for integration testing.

    Attributes:
        git: RealGit instance for integration testing
        repo: Path to the real repository root
        detached_wt: Path to the real detached HEAD worktree
    """

    git: Git
    repo: Path
    detached_wt: Path


class GitWithExistingBranch(NamedTuple):
    """Result of git operations setup with existing branch for integration testing.

    Attributes:
        git: RealGit instance for integration testing
        repo: Path to the real repository root
        wt_path: Path to a worktree location (not yet created, for testing add_worktree)
    """

    git: Git
    repo: Path
    wt_path: Path


def init_git_repo(repo_path: Path, default_branch: str = "main") -> None:
    """Initialize a git repository with initial commit."""
    subprocess.run(["git", "init", "-b", default_branch], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)


@pytest.fixture
def git_ops(
    tmp_path: Path,
) -> Iterator[GitSetup]:
    """Provide RealGit with setup repo for integration testing.

    Returns a GitSetup namedtuple with (git_ops, repo) where repo is the path
    to a real git repository that can be used for testing.

    Uses actual git subprocess calls on tmp_path repo for integration testing.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    yield GitSetup(git=RealGit(), repo=repo)


@pytest.fixture
def git_ops_with_worktrees(
    tmp_path: Path,
) -> Iterator[GitWithWorktrees]:
    """Provide RealGit with multiple pre-configured worktrees for integration testing.

    Returns a GitWithWorktrees namedtuple with (git_ops, repo, worktrees)
    where worktrees is a list of worktree paths created via 'git worktree add'.

    Creates actual worktrees via git for integration testing.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    wt1 = tmp_path / "wt1"
    wt2 = tmp_path / "wt2"

    # Create real worktrees
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-1", str(wt1)],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-2", str(wt2)],
        cwd=repo,
        check=True,
    )
    yield GitWithWorktrees(git=RealGit(), repo=repo, worktrees=[wt1, wt2])


@pytest.fixture
def git_ops_with_detached(
    tmp_path: Path,
) -> Iterator[GitWithDetached]:
    """Provide RealGit with a detached HEAD worktree for integration testing.

    Returns a GitWithDetached namedtuple with (git_ops, repo, detached_wt).

    Creates actual detached HEAD worktree via git for integration testing.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    wt_detached = tmp_path / "detached"

    subprocess.run(
        ["git", "worktree", "add", "--detach", str(wt_detached)],
        cwd=repo,
        check=True,
    )
    yield GitWithDetached(git=RealGit(), repo=repo, detached_wt=wt_detached)


@pytest.fixture
def git_ops_with_existing_branch(
    tmp_path: Path,
) -> Iterator[GitWithExistingBranch]:
    """Provide RealGit with existing branch and worktree path for integration testing.

    Returns a GitWithExistingBranch namedtuple with (git_ops, repo, wt_path).

    Creates real git repository for integration testing.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    wt = tmp_path / "wt"

    yield GitWithExistingBranch(git=RealGit(), repo=repo, wt_path=wt)
