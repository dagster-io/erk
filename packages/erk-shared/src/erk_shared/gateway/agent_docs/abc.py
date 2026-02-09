"""Agent documentation gateway ABC.

This gateway provides access to files in the docs/learned/ directory.
All paths are relative to docs/learned/.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class AgentDocs(ABC):
    """Abstract gateway for agent documentation operations."""

    @abstractmethod
    def has_docs_dir(self, project_root: Path) -> bool:
        """Check if docs/learned/ directory exists.

        Args:
            project_root: Root of the project

        Returns:
            True if docs/learned/ directory exists
        """
        ...

    @abstractmethod
    def list_files(self, project_root: Path) -> list[str]:
        """List all markdown files in docs/learned/ directory.

        Args:
            project_root: Root of the project

        Returns:
            List of relative paths under docs/learned/ (e.g., "architecture/subprocess-wrappers.md")
        """
        ...

    @abstractmethod
    def read_file(self, project_root: Path, rel_path: str) -> str | None:
        """Read a file from docs/learned/ directory.

        Args:
            project_root: Root of the project
            rel_path: Relative path under docs/learned/
                (e.g., "architecture/subprocess-wrappers.md")

        Returns:
            File content, or None if file not found
        """
        ...

    @abstractmethod
    def write_file(self, project_root: Path, rel_path: str, content: str) -> None:
        """Write a file to docs/learned/ directory.

        Creates parent directories as needed.

        Args:
            project_root: Root of the project
            rel_path: Relative path under docs/learned/
                (e.g., "architecture/subprocess-wrappers.md")
            content: File content to write
        """
        ...

    @abstractmethod
    def format_markdown(self, content: str) -> str:
        """Format markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Formatted markdown content
        """
        ...
