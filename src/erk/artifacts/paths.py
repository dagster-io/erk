"""Bundled artifact path utilities.

These utilities locate bundled .claude/, .erk/, and .github/ directories in the erk package.
Extracted to a separate module to avoid circular dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path


@cache
def _get_erk_package_dir() -> Path:
    """Get the erk package directory (where erk/__init__.py lives)."""
    # __file__ is .../erk/artifacts/paths.py, so parent.parent is erk/
    return Path(__file__).parent.parent


def _is_editable_install() -> bool:
    """Check if erk is installed in editable mode.

    Editable: erk package is in src/ layout (e.g., .../src/erk/)
    Wheel: erk package is in site-packages (e.g., .../site-packages/erk/)
    """
    return "site-packages" not in str(_get_erk_package_dir().resolve())


@cache
def get_bundled_claude_dir() -> Path:
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
def get_bundled_codex_dir() -> Path:
    """Get path to bundled .codex/ directory in installed erk package.

    For wheel installs: .codex/ is bundled as package data at erk/data/codex/
    via pyproject.toml force-include. Skills are mapped from .claude/skills/
    to erk/data/codex/skills/ with Codex-compatible frontmatter.

    For editable installs: .codex/ doesn't exist in the repo. Falls back to
    .claude/ since the file formats are identical (both use YAML frontmatter
    with name and description). The install step handles target directory mapping.
    """
    erk_package_dir = _get_erk_package_dir()

    if _is_editable_install():
        # Editable: return .claude/ (same format, install step handles target mapping)
        return erk_package_dir.parent.parent / ".claude"

    # Wheel install: data is bundled at erk/data/codex/
    return erk_package_dir / "data" / "codex"


@cache
def get_bundled_erk_dir() -> Path:
    """Get path to bundled .erk/ directory in installed erk package.

    For wheel installs: .erk/ is bundled as package data at erk/data/erk/
    via pyproject.toml force-include.

    For editable installs: .erk/ is at the erk repo root (no wheel is built,
    so erk/data/ doesn't exist).
    """
    erk_package_dir = _get_erk_package_dir()

    if _is_editable_install():
        # Editable: erk package is at src/erk/, repo root is ../..
        erk_repo_root = erk_package_dir.parent.parent
        return erk_repo_root / ".erk"

    # Wheel install: data is bundled at erk/data/erk/
    return erk_package_dir / "data" / "erk"


@cache
def get_bundled_github_dir() -> Path:
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


@dataclass(frozen=True)
class ErkPackageInfo:
    """Consolidated erk package installation info.

    Bundles is_in_erk_repo detection, bundled directory paths, and current
    version into a single injectable value object. Tests construct directly;
    production code uses the from_project_dir factory.
    """

    in_erk_repo: bool
    bundled_claude_dir: Path
    bundled_github_dir: Path
    bundled_erk_dir: Path
    current_version: str

    @classmethod
    def from_project_dir(cls, project_dir: Path) -> ErkPackageInfo:
        """Create from live package state.

        Uses inline imports to avoid circular dependencies with detection.py
        and release_notes.py.
        """
        from erk.artifacts.detection import is_in_erk_repo
        from erk.core.release_notes import get_current_version

        return cls(
            in_erk_repo=is_in_erk_repo(project_dir),
            bundled_claude_dir=get_bundled_claude_dir(),
            bundled_github_dir=get_bundled_github_dir(),
            bundled_erk_dir=get_bundled_erk_dir(),
            current_version=get_current_version(),
        )
