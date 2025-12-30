"""Detection utilities for artifact management."""

from pathlib import Path


def is_in_erk_repo(project_dir: Path) -> bool:
    """Check if we're running inside the erk repository itself.

    When running in the erk repo, artifacts are read from source
    rather than synced from package data.
    """
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        return False
    content = pyproject.read_text(encoding="utf-8")
    return 'name = "erk"' in content
