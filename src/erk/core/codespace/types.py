"""Data types for codespace registry and GitHub integration."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RegisteredCodespace:
    """A registered codespace in the local registry.

    Represents a "pet" codespace that the user has chosen to track.
    Immutable after construction.
    """

    friendly_name: str
    """User-chosen friendly name (key in registry)."""

    gh_name: str
    """GitHub's opaque codespace name (e.g., 'schrockn-curly-rotary-phone-abc123')."""

    repository: str
    """Repository in owner/repo format."""

    branch: str
    """Branch the codespace was created from."""

    machine_type: str
    """Machine type (e.g., 'standardLinux32gb')."""

    configured: bool
    """Whether the configure wizard has been completed."""

    registered_at: datetime
    """When this codespace was registered."""

    last_connected_at: datetime | None
    """When last connected via erk (None if never connected)."""

    notes: str | None
    """Optional user notes about this codespace."""


@dataclass(frozen=True)
class GitHubCodespaceInfo:
    """Information about a codespace from GitHub.

    Represents live data from the GitHub API via gh CLI.
    """

    name: str
    """GitHub's codespace name."""

    state: str
    """Current state: 'Available', 'Shutdown', 'Starting', 'Pending', etc."""

    repository: str
    """Repository in owner/repo format."""

    branch: str
    """Current branch."""

    machine_type: str
    """Machine type (e.g., 'standardLinux32gb')."""

    created_at: datetime
    """When the codespace was created on GitHub."""
