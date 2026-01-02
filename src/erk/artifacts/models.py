"""Data models for artifact management."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Type of artifact based on directory structure in .claude/ or .github/
# Note: "hook" is not file-based like others; it's a config entry in settings.json
ArtifactType = Literal["skill", "command", "agent", "workflow", "action", "hook"]


@dataclass(frozen=True)
class InstalledArtifact:
    """An artifact installed in a project's .claude/ directory."""

    name: str
    artifact_type: ArtifactType
    path: Path
    # Content hash for staleness detection (optional)
    content_hash: str | None


@dataclass(frozen=True)
class ArtifactFileState:
    """Per-artifact state tracking version and hash at sync time."""

    version: str  # erk version when this artifact was synced
    hash: str  # content hash at sync time


@dataclass(frozen=True)
class ArtifactState:
    """State stored in .erk/state.toml tracking installed artifacts."""

    version: str  # last full sync version (keep for backwards compat)
    files: Mapping[str, ArtifactFileState]  # key: artifact path like "skills/dignified-python"


@dataclass(frozen=True)
class StalenessResult:
    """Result of checking artifact staleness."""

    is_stale: bool
    reason: Literal["not-initialized", "version-mismatch", "up-to-date", "erk-repo"]
    current_version: str
    installed_version: str | None


@dataclass(frozen=True)
class OrphanCheckResult:
    """Result of checking for orphaned artifacts."""

    orphans: dict[str, list[str]]  # folder -> list of orphaned filenames
    skipped_reason: Literal["erk-repo", "no-claude-dir", "no-bundled-dir"] | None


@dataclass(frozen=True)
class CompletenessCheckResult:
    """Result of checking for missing bundled artifacts."""

    missing: dict[str, list[str]]  # folder -> list of missing filenames
    skipped_reason: Literal["erk-repo", "no-claude-dir", "no-bundled-dir"] | None
