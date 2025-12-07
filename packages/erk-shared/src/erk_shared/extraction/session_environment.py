"""Abstract interface for session-related I/O operations.

This module provides an ABC that abstracts the external dependencies
used by session discovery and preprocessing:
- Environment variable access (SESSION_CONTEXT)
- Home directory lookup (Path.home())
- Filesystem operations (path existence, directory listing, file reading)

This enables fake-driven testing of session extraction without mocking.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class SessionEnvironment(ABC):
    """Abstract interface for session-related I/O operations.

    Implementations:
    - RealSessionEnvironment: Production implementation using real filesystem
    - FakeSessionEnvironment: In-memory fake for testing
    """

    @abstractmethod
    def get_session_context_env(self) -> str | None:
        """Get SESSION_CONTEXT environment variable value.

        Returns:
            Value of SESSION_CONTEXT env var, or None if not set
        """
        ...

    @abstractmethod
    def get_home_dir(self) -> Path:
        """Get user home directory.

        Returns:
            Path to user home directory
        """
        ...

    @abstractmethod
    def path_exists(self, path: Path) -> bool:
        """Check if a path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists, False otherwise
        """
        ...

    @abstractmethod
    def is_file(self, path: Path) -> bool:
        """Check if a path is a file.

        Args:
            path: Path to check

        Returns:
            True if path is a file, False otherwise
        """
        ...

    @abstractmethod
    def list_directory(self, path: Path) -> list[Path]:
        """List files in directory (non-recursive).

        Args:
            path: Directory path to list

        Returns:
            List of paths in the directory
        """
        ...

    @abstractmethod
    def get_file_stat(self, path: Path) -> tuple[float, int]:
        """Get file mtime and size.

        Args:
            path: Path to get stats for

        Returns:
            Tuple of (mtime_unix, size_bytes)

        Raises:
            FileNotFoundError: If path does not exist
        """
        ...

    @abstractmethod
    def read_file(self, path: Path) -> str:
        """Read file contents as UTF-8 string.

        Args:
            path: Path to read

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If path does not exist
        """
        ...

    @abstractmethod
    def glob_directory(self, path: Path, pattern: str) -> list[Path]:
        """Glob for files matching pattern in directory.

        Args:
            path: Directory to search in
            pattern: Glob pattern (e.g., "agent-*.jsonl")

        Returns:
            Sorted list of matching paths
        """
        ...
