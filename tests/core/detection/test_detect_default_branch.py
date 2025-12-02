import pytest
from erk_shared.git.fake import FakeGit

from tests.test_utils.paths import sentinel_path


def test_detect_default_branch_uses_remote_head_master() -> None:
    """When remote HEAD points to master, should return master even if main exists."""
    repo_root = sentinel_path()

    git_ops = FakeGit(default_branches={repo_root: "master"})

    assert git_ops.detect_default_branch(repo_root) == "master"


def test_detect_default_branch_uses_remote_head_main() -> None:
    """When remote HEAD points to main, should return main even if master exists."""
    repo_root = sentinel_path()

    git_ops = FakeGit(default_branches={repo_root: "main"})

    assert git_ops.detect_default_branch(repo_root) == "main"


def test_detect_default_branch_fallback_to_main() -> None:
    """When no remote HEAD, falls back to checking if main exists."""
    repo_root = sentinel_path()

    git_ops = FakeGit(default_branches={repo_root: "main"})

    assert git_ops.detect_default_branch(repo_root) == "main"


def test_detect_default_branch_fallback_to_master() -> None:
    """When no remote HEAD and no main, falls back to checking if master exists."""
    repo_root = sentinel_path()

    git_ops = FakeGit(default_branches={repo_root: "master"})

    assert git_ops.detect_default_branch(repo_root) == "master"


def test_detect_default_branch_neither_exists() -> None:
    """When neither main nor master exist, should raise SystemExit."""
    repo_root = sentinel_path()

    git_ops = FakeGit()

    with pytest.raises(SystemExit):
        git_ops.detect_default_branch(repo_root)
