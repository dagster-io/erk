"""CodeReviewsSystemCapability - unified code review workflow infrastructure.

This capability installs the GitHub Actions workflow infrastructure that enables
convention-based code reviews. Individual review definitions are installed
separately via review-* capabilities.

Installs:
- .github/workflows/code-reviews.yml (unified workflow)
- .github/actions/setup-claude-code/ (Claude Code binary installer)
- .github/actions/setup-claude-erk/ (erk tool installer)
- Creates empty .claude/reviews/ directory
"""

import shutil
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
)

InstallableItemType = Literal["file", "directory", "create_directory"]


@dataclass(frozen=True)
class InstallableItem:
    """Declarative definition of an installable artifact."""

    source_path: str  # Relative to bundled .github/ dir (empty for create_directory)
    target_path: str  # Relative to repo root
    item_type: InstallableItemType
    display_name: str


@cache
def _get_installable_items() -> tuple[InstallableItem, ...]:
    """Declarative list of items to install."""
    return (
        InstallableItem(
            source_path="workflows/code-reviews.yml",
            target_path=".github/workflows/code-reviews.yml",
            item_type="file",
            display_name="code-reviews.yml",
        ),
        InstallableItem(
            source_path="actions/setup-claude-code",
            target_path=".github/actions/setup-claude-code",
            item_type="directory",
            display_name="setup-claude-code/",
        ),
        InstallableItem(
            source_path="actions/setup-claude-erk",
            target_path=".github/actions/setup-claude-erk",
            item_type="directory",
            display_name="setup-claude-erk/",
        ),
        InstallableItem(
            source_path="",
            target_path=".claude/reviews",
            item_type="create_directory",
            display_name=".claude/reviews/",
        ),
    )


@cache
def _get_uninstallable_items() -> tuple[InstallableItem, ...]:
    """Items to remove on uninstall (excludes .claude/reviews/ which may have user content)."""
    return tuple(
        item for item in _get_installable_items() if item.item_type != "create_directory"
    )


class CodeReviewsSystemCapability(Capability):
    """GitHub Actions infrastructure for convention-based code reviews.

    Installs:
    - .github/workflows/code-reviews.yml (unified workflow)
    - .github/actions/setup-claude-code/ (Claude Code binary installer)
    - .github/actions/setup-claude-erk/ (erk tool installer)
    - Creates empty .claude/reviews/ directory
    """

    @property
    def name(self) -> str:
        return "code-reviews-system"

    @property
    def description(self) -> str:
        return "GitHub Actions infrastructure for convention-based code reviews"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".github/workflows/code-reviews.yml exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".github/workflows/code-reviews.yml",
                artifact_type="file",
            ),
            CapabilityArtifact(
                path=".github/actions/setup-claude-code/",
                artifact_type="directory",
            ),
            CapabilityArtifact(
                path=".github/actions/setup-claude-erk/",
                artifact_type="directory",
            ),
            CapabilityArtifact(
                path=".claude/reviews/",
                artifact_type="directory",
            ),
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare workflow and actions as managed artifacts."""
        return [
            ManagedArtifact(name="code-reviews", artifact_type="workflow"),
            ManagedArtifact(name="setup-claude-code", artifact_type="action"),
            ManagedArtifact(name="setup-claude-erk", artifact_type="action"),
        ]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if the workflow file exists."""
        if repo_root is None:
            return False
        return (repo_root / ".github" / "workflows" / "code-reviews.yml").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install the workflow and supporting actions."""
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="CodeReviewsSystemCapability requires repo_root",
            )
        # Inline import: avoids circular dependency with artifacts module
        from erk.artifacts.state import add_installed_capability
        from erk.artifacts.sync import get_bundled_github_dir

        bundled_github_dir = get_bundled_github_dir()

        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        installed_items: list[str] = []

        for item in _get_installable_items():
            target = repo_root / item.target_path

            if item.item_type == "file":
                source = bundled_github_dir / item.source_path
                if source.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    installed_items.append(item.display_name)

            elif item.item_type == "directory":
                source = bundled_github_dir / item.source_path
                if source.exists():
                    self._copy_directory(source, target)
                    installed_items.append(item.display_name)

            elif item.item_type == "create_directory":
                target.mkdir(parents=True, exist_ok=True)
                installed_items.append(item.display_name)

        if not installed_items:
            return CapabilityResult(
                success=False,
                message="No code-reviews-system artifacts found in erk package",
            )

        # Record capability installation
        add_installed_capability(repo_root, self.name)

        items_str = ", ".join(installed_items)
        return CapabilityResult(
            success=True,
            message=f"Installed code-reviews-system ({len(installed_items)} items: {items_str})",
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Remove the code-reviews-system workflow and actions.

        Note: .claude/reviews/ is not removed as it may contain user-installed reviews.
        """
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="CodeReviewsSystemCapability requires repo_root",
            )
        from erk.artifacts.state import remove_installed_capability

        removed: list[str] = []

        for item in _get_uninstallable_items():
            target = repo_root / item.target_path

            if item.item_type == "file" and target.exists():
                target.unlink()
                removed.append(item.display_name)

            elif item.item_type == "directory" and target.exists():
                shutil.rmtree(target)
                removed.append(item.display_name)

        remove_installed_capability(repo_root, self.name)

        if not removed:
            return CapabilityResult(
                success=True,
                message="code-reviews-system not installed",
            )

        return CapabilityResult(
            success=True,
            message=f"Removed {', '.join(removed)}",
        )

    def _copy_directory(self, source: Path, target: Path) -> None:
        """Copy directory contents recursively."""
        target.mkdir(parents=True, exist_ok=True)
        for source_path in source.rglob("*"):
            if source_path.is_file():
                relative = source_path.relative_to(source)
                target_path = target / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
