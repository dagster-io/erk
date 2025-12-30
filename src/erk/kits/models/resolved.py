"""Resolved kit types for installation operations."""

from dataclasses import dataclass
from pathlib import Path

from erk.kits.models.types import SourceType


@dataclass(frozen=True)
class ResolvedKit:
    """A kit resolved from a source, ready for installation.

    This dataclass represents a kit that has been located and validated,
    containing all the information needed to install its artifacts.
    """

    kit_id: str  # Globally unique kit identifier
    source_type: SourceType
    version: str
    manifest_path: Path
    artifacts_base: Path


class ArtifactConflictError(Exception):
    """Artifact installation conflicts.

    Raised when an artifact cannot be installed because a file already
    exists at the target location and overwrite is not enabled.
    """

    def __init__(
        self,
        artifact_path: Path,
        suggestion: str = "Use --force to replace existing files",
    ) -> None:
        self.artifact_path = artifact_path
        self.suggestion = suggestion
        super().__init__(f"Artifact already exists: {artifact_path}\n{suggestion}")
