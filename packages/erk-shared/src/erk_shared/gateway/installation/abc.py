"""Erk installation information abstraction.

This module provides an ABC for accessing erk installation details (bundled paths,
version) to enable testable code that doesn't rely on package introspection.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class ErkInstallation(ABC):
    """Abstract interface for erk installation and version info.

    Provides access to bundled artifact directories and version information.
    """

    @abstractmethod
    def get_bundled_claude_dir(self) -> Path:
        """Get path to bundled .claude/ directory in installed erk package.

        For wheel installs: .claude/ is bundled as package data at erk/data/claude/
        For editable installs: .claude/ is at the erk repo root

        Returns:
            Path to the bundled .claude/ directory
        """
        ...

    @abstractmethod
    def get_bundled_github_dir(self) -> Path:
        """Get path to bundled .github/ directory in installed erk package.

        For wheel installs: .github/ is bundled as package data at erk/data/github/
        For editable installs: .github/ is at the erk repo root

        Returns:
            Path to the bundled .github/ directory
        """
        ...

    @abstractmethod
    def get_current_version(self) -> str:
        """Get the currently installed version of erk.

        Returns:
            Version string (e.g., '0.2.1')
        """
        ...
