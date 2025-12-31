"""Data models for artifact management."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Type of artifact based on directory structure in .claude/
ArtifactType = Literal["skill", "command", "agent"]


@dataclass(frozen=True)
class InstalledArtifact:
    """An artifact installed in a project's .claude/ directory."""

    name: str
    artifact_type: ArtifactType
    path: Path
    # Content hash for staleness detection (optional)
    content_hash: str | None


@dataclass(frozen=True)
class ArtifactState:
    """State stored in .erk/state.toml tracking installed artifacts."""

    version: str


@dataclass(frozen=True)
class StalenessResult:
    """Result of checking artifact staleness."""

    is_stale: bool
    reason: Literal["not-initialized", "version-mismatch", "up-to-date", "erk-repo"]
    current_version: str
    installed_version: str | None
