"""Domain-driven session storage abstraction.

This module provides a storage-agnostic interface for session operations.
All filesystem details are hidden behind the SessionStore ABC.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Session:
    """Domain object representing a discovered session.

    Unlike SessionInfo, this type does NOT expose the filesystem path.
    Storage details are hidden behind the SessionStore interface.
    """

    session_id: str
    size_bytes: int
    modified_at: float  # Unix timestamp
    is_current: bool


@dataclass(frozen=True)
class SessionContent:
    """Raw content from a session and its agent logs.

    Contains raw JSONL strings - preprocessing is done separately.
    """

    main_content: str  # Raw JSONL string
    agent_logs: list[tuple[str, str]]  # (agent_id, raw JSONL content)


class ClaudeCodeSessionStore(ABC):
    """Domain-driven interface for session storage operations.

    Hides all storage implementation details. No paths exposed in the public API.
    Projects are identified by working directory context, sessions by ID.
    """

    @abstractmethod
    def has_project(self, project_cwd: Path) -> bool:
        """Check if a Claude Code project exists for the given working directory.

        Args:
            project_cwd: The project's working directory (used as lookup key)

        Returns:
            True if project exists, False otherwise
        """
        ...

    @abstractmethod
    def find_sessions(
        self,
        project_cwd: Path,
        *,
        current_session_id: str | None = None,
        min_size: int = 0,
        limit: int = 10,
    ) -> list[Session]:
        """Find sessions for a project.

        Args:
            project_cwd: Project working directory (used as lookup key)
            current_session_id: Current session ID (for marking is_current)
            min_size: Minimum session size in bytes
            limit: Maximum sessions to return

        Returns:
            Sessions sorted by modified_at descending (newest first).
            Empty list if project doesn't exist.
        """
        ...

    @abstractmethod
    def read_session(
        self,
        project_cwd: Path,
        session_id: str,
        *,
        include_agents: bool = True,
    ) -> SessionContent | None:
        """Read raw session content.

        Args:
            project_cwd: Project working directory (used as lookup key)
            session_id: Session to read
            include_agents: Whether to include agent log content

        Returns:
            SessionContent with raw JSONL strings, or None if not found.
        """
        ...

    @abstractmethod
    def get_latest_plan(
        self,
        project_cwd: Path,
        *,
        session_id: str | None = None,
    ) -> str | None:
        """Get the latest plan from ~/.claude/plans/, optionally session-scoped.

        Args:
            project_cwd: Project working directory (for session lookup hint)
            session_id: Optional session ID for session-scoped lookup

        Returns:
            Plan content as markdown string, or None if no plan found
        """
        ...
