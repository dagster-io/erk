"""Artifact metadata models."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal


class ArtifactSource(Enum):
    """Source type of an installed artifact."""

    MANAGED = "managed"  # Tracked in kits.toml
    LOCAL = "local"  # Created manually, no kit association


class ArtifactLevel(Enum):
    """Installation level of an artifact."""

    USER = "user"  # Installed in ~/.claude/
    PROJECT = "project"  # Installed in ./.claude/


# Artifact type literals
ArtifactType = Literal["skill", "command", "agent", "hook", "doc", "workflow"]
ArtifactTypePlural = Literal["skills", "commands", "agents", "hooks", "docs", "workflows"]

# Mapping from singular to plural forms
ARTIFACT_TYPE_PLURALS: dict[ArtifactType, ArtifactTypePlural] = {
    "skill": "skills",
    "command": "commands",
    "agent": "agents",
    "hook": "hooks",
    "doc": "docs",
    "workflow": "workflows",
}

# Target directories for artifact types (relative to project root)
# Most artifacts go to .claude/, but workflows go to .github/
ARTIFACT_TARGET_DIRS: dict[ArtifactType, str] = {
    "skill": ".claude",
    "command": ".claude",
    "agent": ".claude",
    "hook": ".claude",
    "doc": ".claude",
    "workflow": ".github",
}


@dataclass(frozen=True)
class InstalledArtifact:
    """Represents an installed artifact with its metadata."""

    artifact_type: ArtifactType
    artifact_name: str  # Display name
    file_path: Path  # Actual file location relative to .claude/
    source: ArtifactSource
    level: ArtifactLevel
    kit_id: str | None = None
    kit_version: str | None = None
    settings_source: str | None = None  # For hooks: "settings.json" or "settings.local.json"
