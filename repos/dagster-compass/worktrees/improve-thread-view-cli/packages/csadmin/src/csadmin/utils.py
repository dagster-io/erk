"""Utility functions for csadmin CLI."""

import os
from pathlib import Path

import pygit2


def get_project_path() -> Path | None:
    """
    Find the context store project root by:
    1. Starting from current directory
    2. Looking for contextstore_project.yaml in current directory or its parents
    3. If found in git repository, start from git root

    Returns:
        Path | None: The directory containing contextstore_project.yaml, or None if not found.
    """
    cwd = Path(os.getcwd())

    # First check if contextstore_project.yaml exists in current directory or parents
    current = cwd
    while current != current.parent:  # Stop at root directory
        if (current / "contextstore_project.yaml").exists():
            return current
        current = current.parent

    # If not found, try git repository root approach
    try:
        repo = pygit2.discover_repository(str(cwd))
        if repo:
            git_root = Path(repo).parent
            current = git_root
            while current != current.parent:  # Stop at root directory
                if (current / "contextstore_project.yaml").exists():
                    return current
                current = current.parent
    except pygit2.GitError:
        pass

    return None
