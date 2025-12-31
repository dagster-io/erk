"""Tests for build configuration validation."""

import tomllib
from pathlib import Path


def _get_repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).parent.parent.parent


def test_forced_include_paths_exist() -> None:
    """Verify all source paths in pyproject.toml force-include exist."""
    repo_root = _get_repo_root()
    pyproject_path = repo_root / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    force_include = (
        config.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("force-include", {})
    )

    missing = []
    for source in force_include:
        source_path = repo_root / source
        if not source_path.exists():
            missing.append(source)

    assert not missing, f"Missing forced-include sources: {missing}"
