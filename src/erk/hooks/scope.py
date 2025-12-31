"""Hook scoping utilities for monorepo support."""

import subprocess
from pathlib import Path


def is_in_managed_project() -> bool:
    """Check if cwd is within an erk-managed project.

    Detection: Looks for .erk directory at git repo root. This directory is
    created when erk is initialized, indicating the project is managed by erk.

    Returns:
        True if in a managed project, False otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        repo_root = Path(result.stdout.strip())
        return (repo_root / ".erk").is_dir()
    except subprocess.CalledProcessError:
        # Not in a git repo
        return False
