import pytest

from erk.core.git.fake import FakeGit
from tests.test_utils.paths import sentinel_path


def test_detect_trunk_branch_returns_master() -> None:
    """When trunk branches configured with master, should return master."""
    repo_root = sentinel_path()

    git_ops = FakeGit(trunk_branches={repo_root: "master"})

    assert git_ops.detect_trunk_branch(repo_root) == "master"


def test_detect_trunk_branch_returns_main() -> None:
    """When trunk branches configured with main, should return main."""
    repo_root = sentinel_path()

    git_ops = FakeGit(trunk_branches={repo_root: "main"})

    assert git_ops.detect_trunk_branch(repo_root) == "main"


def test_detect_trunk_branch_fallback_to_main() -> None:
    """When trunk branch not configured, falls back to 'main'."""
    repo_root = sentinel_path()

    git_ops = FakeGit()

    assert git_ops.detect_trunk_branch(repo_root) == "main"


def test_validate_trunk_branch_success() -> None:
    """When configured trunk branch exists, validation succeeds."""
    repo_root = sentinel_path()

    git_ops = FakeGit(trunk_branches={repo_root: "main"})

    # Should not raise
    git_ops.validate_trunk_branch(repo_root, "main")


def test_validate_trunk_branch_failure() -> None:
    """When configured trunk branch doesn't exist, should raise RuntimeError."""
    repo_root = sentinel_path()

    git_ops = FakeGit(trunk_branches={repo_root: "main"})

    with pytest.raises(RuntimeError, match="does not exist in repository"):
        git_ops.validate_trunk_branch(repo_root, "nonexistent")
