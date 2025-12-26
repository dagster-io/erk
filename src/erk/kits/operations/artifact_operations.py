"""Artifact installation and cleanup strategies.

This module provides the strategy for installing and cleaning up kit artifacts
using file copy operations.
"""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path

# Protected source directories that should never be deleted by kit operations.
# These contain SOURCE files that are the source of truth for kit artifacts.
PROTECTED_SOURCE_DIRS: frozenset[str] = frozenset(
    [
        ".claude",
        ".erk/docs",
        ".github/workflows",
    ]
)


def _is_protected_source_path(artifact_path: str) -> bool:
    """Check if path is in a protected source directory.

    Protected directories contain SOURCE files that are the source of truth.
    Kit operations should never delete these files.

    Args:
        artifact_path: Relative path to check (e.g., ".claude/commands/foo.md")

    Returns:
        True if path is protected and should not be deleted
    """
    for protected_dir in PROTECTED_SOURCE_DIRS:
        if artifact_path.startswith(protected_dir + "/") or artifact_path == protected_dir:
            return True
    return False


class ArtifactOperations(ABC):
    """Strategy for installing and cleaning up artifacts."""

    @abstractmethod
    def install_artifact(self, source: Path, target: Path) -> str:
        """Install artifact from source to target.

        Args:
            source: Source file path
            target: Target file path

        Returns:
            Status message suffix for logging (e.g., "")
        """
        pass

    @abstractmethod
    def remove_artifacts(self, artifact_paths: list[str], project_dir: Path) -> list[str]:
        """Remove old artifacts.

        Args:
            artifact_paths: List of artifact paths relative to project_dir
            project_dir: Project root directory

        Returns:
            List of artifact paths that were skipped (not removed)
        """
        pass


class ProdOperations(ArtifactOperations):
    """Production strategy: copy artifacts and delete all on cleanup."""

    def install_artifact(self, source: Path, target: Path) -> str:
        """Copy artifact from source to target."""
        # Ensure parent directories exist
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)

        content = source.read_text(encoding="utf-8")
        target.write_text(content, encoding="utf-8")
        return ""

    def remove_artifacts(self, artifact_paths: list[str], project_dir: Path) -> list[str]:
        """Remove artifacts, protecting source directories.

        Protected source directories (.claude/, .erk/docs/, .github/workflows/)
        are never deleted, even if listed in artifact_paths. This prevents
        accidental deletion of source files during kit reinstallation.

        Returns:
            List of paths that were skipped (protected or non-existent)
        """
        skipped: list[str] = []

        for artifact_path in artifact_paths:
            # Skip protected source directories
            if _is_protected_source_path(artifact_path):
                skipped.append(artifact_path)
                continue

            full_path = project_dir / artifact_path
            if not full_path.exists():
                skipped.append(artifact_path)
                continue

            if full_path.is_file() or full_path.is_symlink():
                full_path.unlink()
            else:
                shutil.rmtree(full_path)

        return skipped


def create_artifact_operations() -> ArtifactOperations:
    """Factory that creates artifact operation strategies.

    Returns:
        ProdOperations (always uses copy-based installation)
    """
    return ProdOperations()
