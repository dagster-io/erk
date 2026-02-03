"""Capability checking utilities for conditional CLI command registration."""

from pathlib import Path

from erk_shared.gateway.git.repo_ops.real import RealGitRepoOps


def is_learned_docs_available() -> bool:
    """Check if the learned-docs capability is available.

    Returns True if docs/learned/ exists in the current repository root,
    False otherwise. Returns False outside a git repo.
    """
    repo_ops = RealGitRepoOps()
    # LBYL: get_git_common_dir returns None gracefully outside a git repo,
    # unlike get_repository_root which raises CalledProcessError
    git_common_dir = repo_ops.get_git_common_dir(Path.cwd())
    if git_common_dir is None:
        return False
    repo_root = repo_ops.get_repository_root(Path.cwd())
    return (repo_root / "docs" / "learned").exists()
