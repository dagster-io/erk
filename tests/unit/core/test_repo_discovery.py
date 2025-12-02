"""Unit tests for repository discovery with GitHub identity extraction."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit

from erk.core.repo_discovery import RepoContext, discover_repo_or_sentinel


def test_discover_repo_extracts_github_identity_https(tmp_path: Path):
    """Test that GitHub identity is extracted from HTTPS remote URL."""
    repo_root = tmp_path / "test-repo"
    erk_root = tmp_path / ".erk"

    # Configure FakeGit with a GitHub HTTPS remote
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main", is_root=True)]},
        git_common_dirs={repo_root: repo_root / ".git"},
        existing_paths={repo_root, repo_root / ".git"},
        remote_urls={(repo_root, "origin"): "https://github.com/dagster-io/erk.git"},
    )

    result = discover_repo_or_sentinel(repo_root, erk_root, git_ops)

    assert isinstance(result, RepoContext)
    assert result.github is not None
    assert result.github.owner == "dagster-io"
    assert result.github.repo == "erk"


def test_discover_repo_extracts_github_identity_ssh(tmp_path: Path):
    """Test that GitHub identity is extracted from SSH remote URL."""
    repo_root = tmp_path / "test-repo"
    erk_root = tmp_path / ".erk"

    # Configure FakeGit with a GitHub SSH remote
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main", is_root=True)]},
        git_common_dirs={repo_root: repo_root / ".git"},
        existing_paths={repo_root, repo_root / ".git"},
        remote_urls={(repo_root, "origin"): "git@github.com:dagster-io/erk.git"},
    )

    result = discover_repo_or_sentinel(repo_root, erk_root, git_ops)

    assert isinstance(result, RepoContext)
    assert result.github is not None
    assert result.github.owner == "dagster-io"
    assert result.github.repo == "erk"


def test_discover_repo_no_github_identity_non_github_remote(tmp_path: Path):
    """Test that GitHub identity is None for non-GitHub remotes."""
    repo_root = tmp_path / "test-repo"
    erk_root = tmp_path / ".erk"

    # Configure FakeGit with a non-GitHub remote
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main", is_root=True)]},
        git_common_dirs={repo_root: repo_root / ".git"},
        existing_paths={repo_root, repo_root / ".git"},
        remote_urls={(repo_root, "origin"): "https://gitlab.com/user/repo.git"},
    )

    result = discover_repo_or_sentinel(repo_root, erk_root, git_ops)

    assert isinstance(result, RepoContext)
    assert result.github is None


def test_discover_repo_no_github_identity_no_remote(tmp_path: Path):
    """Test that GitHub identity is None when no remote exists."""
    repo_root = tmp_path / "test-repo"
    erk_root = tmp_path / ".erk"

    # Configure FakeGit without any remote URL
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main", is_root=True)]},
        git_common_dirs={repo_root: repo_root / ".git"},
        existing_paths={repo_root, repo_root / ".git"},
        remote_urls={},  # No remote configured
    )

    result = discover_repo_or_sentinel(repo_root, erk_root, git_ops)

    assert isinstance(result, RepoContext)
    assert result.github is None
