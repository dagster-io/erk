"""Integration tests for RealGitRemoteOps with real git repositories.

Tests get_remote_ref() and get_local_tracking_ref_sha() against actual
git subprocess calls using local bare remotes.
"""

import subprocess
from pathlib import Path

import pytest

from erk_shared.gateway.git.real import RealGit


@pytest.fixture
def repo_with_remote(tmp_path: Path) -> tuple[Path, Path]:
    """Create a local repo with a bare remote for testing ls-remote.

    Returns (repo_path, bare_remote_path).
    """
    bare = tmp_path / "bare.git"
    repo = tmp_path / "repo"

    # Create bare remote
    subprocess.run(["git", "init", "--bare", str(bare)], check=True)

    # Clone it to get a working repo with 'origin' pointing to bare
    subprocess.run(["git", "clone", str(bare), str(repo)], check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    # Create initial commit and push
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)
    subprocess.run(["git", "push", "origin", "HEAD"], cwd=repo, check=True)

    return repo, bare


def test_get_remote_ref_returns_sha_for_existing_ref(
    repo_with_remote: tuple[Path, Path],
) -> None:
    """get_remote_ref returns a valid SHA for a branch pushed to the remote."""
    repo, _bare = repo_with_remote
    git = RealGit()

    # Get the current HEAD SHA for comparison
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()

    # The default branch may be "main" or "master" depending on git config
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()

    result = git.remote.get_remote_ref(repo, "origin", branch)

    assert result is not None
    assert len(result) == 40  # Full SHA hex
    assert result == head_sha


def test_get_remote_ref_returns_none_for_nonexistent_ref(
    repo_with_remote: tuple[Path, Path],
) -> None:
    """get_remote_ref returns None for a ref that doesn't exist on remote."""
    repo, _bare = repo_with_remote
    git = RealGit()

    result = git.remote.get_remote_ref(repo, "origin", "nonexistent-branch-xyz")

    assert result is None


def test_get_local_tracking_ref_sha_after_fetch(
    repo_with_remote: tuple[Path, Path],
) -> None:
    """After fetching, local tracking ref SHA matches what was pushed."""
    repo, _bare = repo_with_remote
    git = RealGit()

    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()

    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()

    result = git.remote.get_local_tracking_ref_sha(repo, "origin", branch)

    assert result is not None
    assert result == head_sha


def test_get_local_tracking_ref_sha_returns_none_before_fetch(
    repo_with_remote: tuple[Path, Path],
) -> None:
    """Local tracking ref doesn't exist for a branch never fetched."""
    repo, _bare = repo_with_remote
    git = RealGit()

    result = git.remote.get_local_tracking_ref_sha(repo, "origin", "never-fetched-branch")

    assert result is None
