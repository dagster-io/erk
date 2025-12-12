"""Git repository utilities for erk.kits."""

import subprocess
from pathlib import Path


def find_git_root(start: Path) -> Path | None:
    """Find git repository root from start path.

    Args:
        start: Directory to start searching from

    Returns:
        Path to git repository root, or None if not in a git repository
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def resolve_project_dir(cwd: Path) -> Path:
    """Resolve project directory, preferring git root over cwd.

    This ensures kit artifacts are installed where Claude Code expects them
    (at the git repo root), even when running from a subdirectory.

    Args:
        cwd: Current working directory

    Returns:
        Git repo root if in a git repo, otherwise returns cwd
    """
    git_root = find_git_root(cwd)
    if git_root is not None:
        return git_root
    return cwd
