"""Artifact installation and cleanup strategies.

This module provides the strategy for installing and cleaning up kit artifacts
using file copy operations.
"""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path


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
        """Remove all artifacts unconditionally."""
        for artifact_path in artifact_paths:
            full_path = project_dir / artifact_path
            if not full_path.exists():
                continue

            if full_path.is_file() or full_path.is_symlink():
                full_path.unlink()
            else:
                shutil.rmtree(full_path)

        return []


def create_artifact_operations() -> ArtifactOperations:
    """Factory that creates artifact operation strategies.

    Returns:
        ProdOperations (always uses copy-based installation)
    """
    return ProdOperations()
