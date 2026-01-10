"""Base classes and types for the capability system.

Capabilities are optional features that can be installed via `erk init capability add <name>`.
Each capability knows how to detect if it's installed and how to install itself.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class CapabilityResult:
    """Result of a capability installation operation."""

    success: bool
    message: str
    created_files: tuple[str, ...] = ()  # Relative paths of files/dirs created


@dataclass(frozen=True)
class CapabilityArtifact:
    """Describes an artifact installed by a capability."""

    path: str  # Relative to repo_root, e.g., "docs/learned/"
    artifact_type: Literal["file", "directory"]


class Capability(ABC):
    """Abstract base class for erk capabilities.

    A capability is an optional feature that can be installed during `erk init`.
    Each capability must implement:
    - name: CLI-facing identifier
    - description: Short description for help text
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
    def is_installed(self, repo_root: Path) -> bool:
        """Check if this capability is already installed.

        Args:
            repo_root: Path to the repository root

        Returns:
            True if the capability is already installed
        """
        ...

    @abstractmethod
    def install(self, repo_root: Path) -> CapabilityResult:
        """Install this capability.

        Args:
            repo_root: Path to the repository root

        Returns:
            CapabilityResult with success status and message
        """
        ...
