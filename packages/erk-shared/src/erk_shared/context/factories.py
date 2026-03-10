"""Factory functions for creating ErkContext instances.

This module provides utility functions for context creation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk_shared.gateway.git.abc import Git
    from erk_shared.gateway.github.types import RepoInfo


def get_repo_info(git: Git, repo_root: Path) -> RepoInfo | None:
    """Detect repository info from git remote URL.

    Parses the origin remote URL to extract owner/name for GitHub API calls.
    Returns None if no origin remote is configured or URL cannot be parsed.

    Args:
        git: Git interface for operations
        repo_root: Repository root path

    Returns:
        RepoInfo with owner/name, or None if not determinable
    """
    from erk_shared.gateway.github.parsing import parse_git_remote_url
    from erk_shared.gateway.github.types import RepoInfo

    try:
        remote_url = git.remote.get_remote_url(repo_root, "origin")
        owner, name = parse_git_remote_url(remote_url)
        return RepoInfo(owner=owner, name=name)
    except ValueError:
        return None
