"""Data models for artifact sync."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactState:
    """State of installed artifacts."""

    version: str


@dataclass(frozen=True)
class StalenessResult:
    """Result of staleness check."""

    is_stale: bool
    reason: str  # e.g., "not initialized", "version mismatch", "up to date"
    current_version: str | None
    installed_version: str | None
