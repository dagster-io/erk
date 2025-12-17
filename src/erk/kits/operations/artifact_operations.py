"""Artifact installation and cleanup strategies.

This module provides the strategy for installing and cleaning up kit artifacts
using file copy operations.
"""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from erk.kits.utils.content_hash import compute_content_hash


class ArtifactOperations(ABC):
    """Strategy for installing and cleaning up artifacts."""

    @abstractmethod
    def install_artifact(self, source: Path, target: Path) -> tuple[str, str]:
        """Install artifact from source to target.

        Args:
            source: Source file path
            target: Target file path

        Returns:
            Tuple of (status_suffix, content_hash) where:
            - status_suffix: Message suffix for logging (e.g., "")
            - content_hash: Hash of installed content (e.g., "sha256:abc...")
        """
        pass

    @abstractmethod
    def remove_artifacts(
        self, artifacts: dict[str, str] | list[str], project_dir: Path
    ) -> list[str]:
        """Remove old artifacts.

        Args:
            artifacts: Dict of path → hash, or legacy list of paths
            project_dir: Project root directory

        Returns:
            List of artifact paths that were skipped (not removed)
        """
        pass


class ProdOperations(ArtifactOperations):
    """Production strategy: copy artifacts and delete all on cleanup."""

    def install_artifact(self, source: Path, target: Path) -> tuple[str, str]:
        """Copy artifact from source to target, returning content hash."""
        # Ensure parent directories exist
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)

        content = source.read_text(encoding="utf-8")
        target.write_text(content, encoding="utf-8")
        content_hash = compute_content_hash(content)
        return ("", content_hash)

    def remove_artifacts(
        self, artifacts: dict[str, str] | list[str], project_dir: Path
    ) -> list[str]:
        """Remove all artifacts unconditionally.

        Accepts either dict (new format) or list (legacy format).
        """
        # Extract paths from dict or use list directly
        artifact_paths = list(artifacts.keys()) if isinstance(artifacts, dict) else artifacts

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
