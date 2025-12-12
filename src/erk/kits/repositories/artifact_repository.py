"""Repository interface for artifact discovery."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk.kits.models.artifact import InstalledArtifact
from erk.kits.models.config import ProjectConfig


class ArtifactRepository(ABC):
    """Abstract interface for artifact discovery operations."""

    @abstractmethod
    def discover_all_artifacts(
        self, project_dir: Path, config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Discover all installed artifacts with their metadata.

        Args:
            project_dir: Project root directory
            config: Project configuration from dot-agent.toml

        Returns:
            List of all installed artifacts with metadata
        """
        pass

    @abstractmethod
    def discover_multi_level(
        self, user_path: Path, project_path: Path, project_config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Discover artifacts from both user and project levels.

        Args:
            user_path: User-level .claude directory (e.g., ~/.claude)
            project_path: Project-level .claude directory (e.g., ./.claude)
            project_config: Project configuration from dot-agent.toml

        Returns:
            List of artifacts from both levels with level annotation
        """
        pass
