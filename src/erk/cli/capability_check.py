"""Capability checking utilities for conditional CLI command registration."""

from pathlib import Path

from erk_shared.gateway.git.repo_ops.abc import GitRepoOps


def is_learned_docs_available(*, repo_ops: GitRepoOps, cwd: Path) -> bool:
    """Check if the learned-docs capability is available.

    Returns True if docs/learned/ exists in the current repository root,
    False otherwise. Returns False outside a git repo.
    """
    # LBYL: get_git_common_dir returns None gracefully outside a git repo,
    # unlike get_repository_root which raises CalledProcessError
    git_common_dir = repo_ops.get_git_common_dir(cwd)
    if git_common_dir is None:
        return False
    repo_root = repo_ops.get_repository_root(cwd)
    return (repo_root / "docs" / "learned").exists()
