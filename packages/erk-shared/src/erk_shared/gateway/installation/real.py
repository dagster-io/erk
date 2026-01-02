"""Real ErkInstallation implementation using package introspection."""

import importlib.metadata
from functools import cache
from pathlib import Path

from erk_shared.gateway.installation.abc import ErkInstallation


@cache
def _get_erk_package_dir() -> Path:
    """Get the erk package directory (where erk/__init__.py lives)."""
    # __file__ is .../erk_shared/gateway/installation/real.py
    # We need to find the erk package, not erk_shared
    # The erk package is a sibling at the workspace level
    # For wheel: both are in site-packages
    # For editable: erk is at src/erk/
    import erk

    return Path(erk.__file__).parent


def _is_editable_install() -> bool:
    """Check if erk is installed in editable mode.

    Editable: erk package is in src/ layout (e.g., .../src/erk/)
    Wheel: erk package is in site-packages (e.g., .../site-packages/erk/)
    """
    return "site-packages" not in str(_get_erk_package_dir().resolve())


@cache
def _get_bundled_claude_dir_cached() -> Path:
    """Get path to bundled .claude/ directory in installed erk package.

    For wheel installs: .claude/ is bundled as package data at erk/data/claude/
    via pyproject.toml force-include.

    For editable installs: .claude/ is at the erk repo root (no wheel is built,
    so erk/data/ doesn't exist).
    """
    erk_package_dir = _get_erk_package_dir()

    if _is_editable_install():
        # Editable: erk package is at src/erk/, repo root is ../..
        erk_repo_root = erk_package_dir.parent.parent
        return erk_repo_root / ".claude"

    # Wheel install: data is bundled at erk/data/claude/
    return erk_package_dir / "data" / "claude"


@cache
def _get_bundled_github_dir_cached() -> Path:
    """Get path to bundled .github/ directory in installed erk package.

    For wheel installs: .github/ is bundled as package data at erk/data/github/
    via pyproject.toml force-include.

    For editable installs: .github/ is at the erk repo root.
    """
    erk_package_dir = _get_erk_package_dir()

    if _is_editable_install():
        # Editable: erk package is at src/erk/, repo root is ../..
        erk_repo_root = erk_package_dir.parent.parent
        return erk_repo_root / ".github"

    # Wheel install: data is bundled at erk/data/github/
    return erk_package_dir / "data" / "github"


class RealErkInstallation(ErkInstallation):
    """Production implementation using package introspection."""

    def get_bundled_claude_dir(self) -> Path:
        """Get path to bundled .claude/ directory in installed erk package."""
        return _get_bundled_claude_dir_cached()

    def get_bundled_github_dir(self) -> Path:
        """Get path to bundled .github/ directory in installed erk package."""
        return _get_bundled_github_dir_cached()

    def get_current_version(self) -> str:
        """Get the currently installed version of erk."""
        return importlib.metadata.version("erk")
