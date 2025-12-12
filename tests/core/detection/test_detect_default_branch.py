import pytest

from erk_shared.git.fake import FakeGit
from tests.test_utils.paths import sentinel_path


def test_detect_trunk_branch_uses_remote_head_master() -> None:
    """When remote HEAD points to master, should return master even if main exists."""
    repo_root = sentinel_path()

    git_ops = FakeGit(trunk_branches={repo_root: "master"})

    assert git_ops.detect_trunk_branch(repo_root) == "master"


def test_detect_trunk_branch_uses_remote_head_main() -> None:
    """When remote HEAD points to main, should return main even if master exists."""
    repo_root = sentinel_path()

    git_ops = FakeGit(trunk_branches={repo_root: "main"})

    assert git_ops.detect_trunk_branch(repo_root) == "main"


def test_detect_trunk_branch_fallback_to_main() -> None:
    """When no remote HEAD, returns 'main' as final fallback."""
    repo_root = sentinel_path()

    git_ops = FakeGit()

    assert git_ops.detect_trunk_branch(repo_root) == "main"


def test_validate_trunk_branch_exists_in_trunk_branches() -> None:
    """validate_trunk_branch succeeds when branch is in trunk_branches dict."""
    repo_root = sentinel_path()

    git_ops = FakeGit(trunk_branches={repo_root: "master"})

    assert git_ops.validate_trunk_branch(repo_root, "master") == "master"


def test_validate_trunk_branch_exists_in_local_branches() -> None:
    """validate_trunk_branch succeeds when branch is in local_branches list."""
    repo_root = sentinel_path()

    git_ops = FakeGit(local_branches={repo_root: ["master", "feature"]})

    assert git_ops.validate_trunk_branch(repo_root, "master") == "master"


def test_validate_trunk_branch_not_exists() -> None:
    """validate_trunk_branch raises RuntimeError when branch doesn't exist."""
    repo_root = sentinel_path()

    git_ops = FakeGit(trunk_branches={repo_root: "main"})

    with pytest.raises(RuntimeError, match="does not exist in repository"):
        git_ops.validate_trunk_branch(repo_root, "nonexistent")
