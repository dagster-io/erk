"""Base classes and types for the capability system.

Capabilities are optional features that can be installed via `erk init capability add <name>`.
Each capability knows how to detect if it's installed and how to install itself.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Type alias for capability scope
CapabilityScope = Literal["project", "user"]

# Artifact types that capabilities can declare they manage
ManagedArtifactType = Literal["skill", "command", "agent", "workflow", "action", "hook", "prompt"]


@dataclass(frozen=True)
class ManagedArtifact:
    """Describes an artifact managed by a capability for artifact detection.

    This bridges capability declarations with artifact detection/health checks.
    Used by the registry to determine which artifacts are erk-managed.
    """

    name: str  # e.g., "dignified-python", "ruff-format-hook"
    artifact_type: ManagedArtifactType


@dataclass(frozen=True)
class CapabilityResult:
    """Result of a capability installation operation."""

    success: bool
    message: str
    created_files: tuple[str, ...] = ()  # Relative paths of files/dirs created


@dataclass(frozen=True)
class CapabilityArtifact:
    """Describes an artifact installed by a capability."""

    path: str  # Relative to repo_root for project-scope, or absolute for user-scope
    artifact_type: Literal["file", "directory"]


class Capability(ABC):
    """Abstract base class for erk capabilities.

    A capability is an optional feature that can be installed during `erk init`.
    Each capability must implement:
    - name: CLI-facing identifier
    - description: Short description for help text
    - scope: Whether this is a "project" or "user" level capability
    - is_installed(): Check if already installed
    - install(): Install the capability
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """CLI-facing identifier for this capability (e.g., 'learned-docs')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description for help text."""
        ...

    @property
    @abstractmethod
    def scope(self) -> CapabilityScope:
        """Whether this capability is project-level or user-level.

        - "project": Installed per-repository (requires repo_root)
        - "user": Installed globally for the user (repo_root is None)
        """
        ...

    @property
    @abstractmethod
    def installation_check_description(self) -> str:
        """Human-readable description of what is_installed() checks.

        Example: "docs/learned/ directory exists"
        """
        ...

    @property
    @abstractmethod
    def artifacts(self) -> list[CapabilityArtifact]:
        """List of artifacts this capability installs.

        Returns:
            List of CapabilityArtifact describing files/directories created
        """
        ...

    @abstractmethod
    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if this capability is already installed.

        Args:
            repo_root: Path to the repository root (None for user-level capabilities)

        Returns:
            True if the capability is already installed
        """
        ...

    @property
    def required(self) -> bool:
        """If True, auto-install during erk init without prompting.

        Default is False. Override to return True for capabilities that should
        always be installed (e.g., hooks).
        """
        return False

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """List of artifacts this capability manages for artifact detection.

        Used by the registry to determine which artifacts are erk-managed
        (vs project-specific). Override in subclasses to declare managed artifacts.

        Default is empty list for backwards compatibility.
        """
        return []

    def preflight(self, repo_root: Path | None) -> CapabilityResult:
        """Check preconditions before installation.

        Override to add capability-specific checks (e.g., required dependencies).
        Default implementation returns success.

        Args:
            repo_root: Path to the repository root (None for user-level capabilities)

        Returns:
            CapabilityResult with success=False and message if preconditions not met
        """
        return CapabilityResult(success=True, message="")

    @abstractmethod
    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install this capability.

        Args:
            repo_root: Path to the repository root (None for user-level capabilities)

        Returns:
            CapabilityResult with success status and message
        """
        ...

    @abstractmethod
    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Uninstall this capability.

        Args:
            repo_root: Path to the repository root (None for user-level capabilities)

        Returns:
            CapabilityResult with success status and message
        """
        ...
