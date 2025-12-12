"""In-memory fake implementation for testing."""

from pathlib import Path

from erk.kits.models.artifact import InstalledArtifact
from erk.kits.models.config import ProjectConfig
from erk.kits.repositories.artifact_repository import ArtifactRepository


class FakeArtifactRepository(ArtifactRepository):
    """In-memory artifact repository for testing."""

    def __init__(self) -> None:
        """Initialize with empty artifact list."""
        self._artifacts: list[InstalledArtifact] = []

    def add_artifact(self, artifact: InstalledArtifact) -> None:
        """Add a single artifact to the fake repository.

        Args:
            artifact: The artifact to add
        """
        self._artifacts.append(artifact)

    def set_artifacts(self, artifacts: list[InstalledArtifact]) -> None:
        """Set all artifacts at once, replacing any existing ones.

        Args:
            artifacts: List of artifacts to set
        """
        self._artifacts = artifacts.copy()

    def clear(self) -> None:
        """Remove all artifacts from the repository."""
        self._artifacts = []

    def discover_all_artifacts(
        self, project_dir: Path, config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Return pre-configured artifacts.

        Note: This ignores the project_dir and config parameters
        and simply returns the artifacts that have been set up via
        add_artifact() or set_artifacts().

        Args:
            project_dir: Ignored - not used in fake implementation
            config: Ignored - not used in fake implementation

        Returns:
            Copy of the list of configured artifacts
        """
        return self._artifacts.copy()

    def discover_multi_level(
        self, user_path: Path, project_path: Path, project_config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Return pre-configured artifacts from multiple levels.

        Note: This ignores the path and config parameters
        and simply returns the artifacts that have been set up via
        add_artifact() or set_artifacts().

        Args:
            user_path: Ignored - not used in fake implementation
            project_path: Ignored - not used in fake implementation
            project_config: Ignored - not used in fake implementation

        Returns:
            Copy of the list of configured artifacts
        """
        return self._artifacts.copy()
