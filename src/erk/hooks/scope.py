"""Hook scoping utilities for monorepo support."""

import subprocess
from pathlib import Path


def is_in_managed_project() -> bool:
    """Check if cwd is within a dot-agent managed project.

    Detection: Looks for .erk/kits.toml at git repo root. This file is created
    when kits are installed, indicating the project is managed by dot-agent.

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
        return (repo_root / ".erk" / "kits.toml").exists()
    except subprocess.CalledProcessError:
        # Not in a git repo
        return False
