"""Capability checking utilities for conditional CLI command registration."""

from pathlib import Path

from erk_shared.gateway.git.real import RealGit


def is_learned_docs_available() -> bool:
    """Check if the learned-docs capability is available.

    Returns True if docs/learned/ exists in the current repository root,
    False otherwise. Falls back to False outside a git repo or if any error occurs.
    """
    try:
        git = RealGit()
        repo_root = git.repo.get_repository_root(Path.cwd())
        if repo_root is None:
            return False
        return (repo_root / "docs" / "learned").exists()
    except Exception:
        return False
