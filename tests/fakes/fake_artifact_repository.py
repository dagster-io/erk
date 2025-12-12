"""Fake implementation of ArtifactRepository for testing."""

from pathlib import Path

from erk.kits.models.artifact import InstalledArtifact
from erk.kits.models.config import ProjectConfig
from erk.kits.repositories.artifact_repository import ArtifactRepository


class FakeArtifactRepository(ArtifactRepository):
    """Fake artifact repository for testing.

    This implementation returns pre-configured artifacts rather than
    discovering them from the filesystem.
    """

    def __init__(self, artifacts: list[InstalledArtifact] | None = None) -> None:
        """Initialize with optional list of artifacts.

        Args:
            artifacts: Pre-configured list of artifacts to return
        """
        self._artifacts: list[InstalledArtifact] = artifacts or []

    def set_artifacts(self, artifacts: list[InstalledArtifact]) -> None:
        """Set the artifacts to return from discovery.

        Args:
            artifacts: List of artifacts to return
        """
        self._artifacts = artifacts

    def discover_all_artifacts(
        self, project_dir: Path, config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Return pre-configured artifacts.

        Args:
            project_dir: Project root directory (unused)
            config: Project configuration (unused)

        Returns:
            Pre-configured list of artifacts
        """
        return self._artifacts

    def discover_multi_level(
        self, user_path: Path, project_path: Path, project_config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Return pre-configured artifacts.

        Args:
            user_path: User-level .claude directory (unused)
            project_path: Project-level .claude directory (unused)
            project_config: Project configuration (unused)

        Returns:
            Pre-configured list of artifacts
        """
        return self._artifacts
