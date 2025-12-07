"""In-memory fake for testing session environment operations.

Follows constructor injection pattern - all state via kwargs.
"""

from fnmatch import fnmatch
from pathlib import Path

from erk_shared.extraction.session_environment import SessionEnvironment


class FakeSessionEnvironment(SessionEnvironment):
    """In-memory fake for testing session environment operations.

    Follows constructor injection pattern - all state via kwargs.

    Example:
        fake_env = FakeSessionEnvironment(
            session_context="session_id=abc-123",
            home_dir=Path("/fake/home"),
            files={
                Path("/fake/home/.claude/projects/proj/session.jsonl"): FileEntry(
                    content='{"type": "user"}\n',
                    mtime=1234567890.0,
                ),
            },
        )
    """

    def __init__(
        self,
        *,
        session_context: str | None = None,
        home_dir: Path | None = None,
        files: dict[Path, "FileEntry"] | None = None,
        directories: set[Path] | None = None,
    ) -> None:
        """Initialize fake session environment.

        Args:
            session_context: Value of SESSION_CONTEXT env var
            home_dir: Simulated home directory path
            files: Dictionary mapping paths to FileEntry objects
            directories: Set of directory paths that exist
        """
        self._session_context = session_context
        self._home_dir = home_dir or Path("/fake/home")
        self._files = files or {}
        self._directories = directories or set()

        # Auto-create parent directories for all files
        for file_path in self._files:
            parent = file_path.parent
            while parent != parent.parent:  # Stop at root
                self._directories.add(parent)
                parent = parent.parent

    def get_session_context_env(self) -> str | None:
        return self._session_context

    def get_home_dir(self) -> Path:
        return self._home_dir

    def path_exists(self, path: Path) -> bool:
        return path in self._files or path in self._directories

    def is_file(self, path: Path) -> bool:
        return path in self._files

    def list_directory(self, path: Path) -> list[Path]:
        """List immediate children of directory."""
        children: list[Path] = []
        seen: set[Path] = set()

        # Find files directly in this directory
        for file_path in self._files:
            if file_path.parent == path and file_path not in seen:
                children.append(file_path)
                seen.add(file_path)

        # Find subdirectories directly in this directory
        for dir_path in self._directories:
            if dir_path.parent == path and dir_path not in seen:
                children.append(dir_path)
                seen.add(dir_path)

        return children

    def get_file_stat(self, path: Path) -> tuple[float, int]:
        if path not in self._files:
            raise FileNotFoundError(f"No stat for {path}")
        entry = self._files[path]
        return (entry.mtime, len(entry.content.encode("utf-8")))

    def read_file(self, path: Path) -> str:
        if path not in self._files:
            raise FileNotFoundError(f"No content for {path}")
        return self._files[path].content

    def glob_directory(self, path: Path, pattern: str) -> list[Path]:
        """Glob for files matching pattern in directory."""
        matches: list[Path] = []
        for file_path in self._files:
            if file_path.parent == path and fnmatch(file_path.name, pattern):
                matches.append(file_path)
        return sorted(matches)


class FileEntry:
    """Represents a file's content and metadata for FakeSessionEnvironment."""

    def __init__(self, content: str, mtime: float = 0.0) -> None:
        """Initialize file entry.

        Args:
            content: File content as string
            mtime: Modification time as Unix timestamp
        """
        self.content = content
        self.mtime = mtime
