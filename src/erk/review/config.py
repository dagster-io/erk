"""Configuration for the review system.

Reads review settings from pyproject.toml [tool.erk.reviews] section.
"""

import tomllib
from pathlib import Path


def read_review_exclude_patterns(project_root: Path) -> tuple[str, ...]:
    """Read exclude patterns from pyproject.toml [tool.erk.reviews].exclude.

    Args:
        project_root: Path to the project root containing pyproject.toml.

    Returns:
        Tuple of gitignore-style glob patterns to exclude from reviews.
        Returns empty tuple if config is missing or malformed.
    """
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        return ()

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    erk_config = data.get("tool", {}).get("erk", {}).get("reviews", {})
    exclude = erk_config.get("exclude", [])

    if not isinstance(exclude, list):
        return ()

    return tuple(item for item in exclude if isinstance(item, str))
