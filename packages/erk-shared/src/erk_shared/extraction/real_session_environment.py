"""Production implementation of SessionEnvironment using real filesystem."""

import os
from pathlib import Path

from erk_shared.extraction.session_environment import SessionEnvironment


class RealSessionEnvironment(SessionEnvironment):
    """Production implementation using real filesystem and env vars."""

    def get_session_context_env(self) -> str | None:
        return os.environ.get("SESSION_CONTEXT")

    def get_home_dir(self) -> Path:
        return Path.home()

    def path_exists(self, path: Path) -> bool:
        return path.exists()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def list_directory(self, path: Path) -> list[Path]:
        return list(path.iterdir())

    def get_file_stat(self, path: Path) -> tuple[float, int]:
        stat = path.stat()
        return (stat.st_mtime, stat.st_size)

    def read_file(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def glob_directory(self, path: Path, pattern: str) -> list[Path]:
        return sorted(path.glob(pattern))
