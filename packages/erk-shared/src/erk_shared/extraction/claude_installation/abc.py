"""Domain-driven Claude installation abstraction.

This module provides a storage-agnostic interface for Claude installation operations.
All filesystem details are hidden behind the ClaudeInstallation ABC.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from erk_shared.non_ideal_state import SessionNotFound


@dataclass(frozen=True)
class Session:
    """Domain object representing a discovered session.

    Unlike SessionInfo, this type does NOT expose the filesystem path.
    Storage details are hidden behind the ClaudeInstallation interface.
    """

    session_id: str
    size_bytes: int
    modified_at: float  # Unix timestamp
    is_current: bool
    parent_session_id: str | None = None  # For agent sessions


@dataclass(frozen=True)
class SessionContent:
    """Raw content from a session and its agent logs.

    Contains raw JSONL strings - preprocessing is done separately.
    """

    main_content: str  # Raw JSONL string
    agent_logs: list[tuple[str, str]]  # (agent_id, raw JSONL content)


class ClaudeInstallation(ABC):
    """Domain-driven interface for Claude installation operations.

    Hides all storage implementation details. No paths exposed in the public API.
    Projects are identified by working directory context, sessions by ID.
    """

    # --- Session operations ---

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
        current_session_id: str | None,
        min_size: int,
        limit: int,
        include_agents: bool,
    ) -> list[Session]:
        """Find sessions for a project.

        Args:
            project_cwd: Project working directory (used as lookup key)
            current_session_id: Current session ID (for marking is_current)
            min_size: Minimum session size in bytes
            limit: Maximum sessions to return
            include_agents: Whether to include agent sessions in the listing

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
        include_agents: bool,
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
        session_id: str | None,
    ) -> str | None:
        """Get the latest plan from ~/.claude/plans/, optionally session-scoped.

        Args:
            project_cwd: Project working directory (for session lookup hint)
            session_id: Optional session ID for session-scoped lookup

        Returns:
            Plan content as markdown string, or None if no plan found
        """
        ...

    @abstractmethod
    def get_session(
        self,
        project_cwd: Path,
        session_id: str,
    ) -> Session | SessionNotFound:
        """Get a specific session by ID.

        Args:
            project_cwd: Project working directory (used as lookup key)
            session_id: Session ID to retrieve

        Returns:
            Session if found, SessionNotFound sentinel otherwise
        """
        ...

    @abstractmethod
    def get_session_path(
        self,
        project_cwd: Path,
        session_id: str,
    ) -> Path | None:
        """Get the file path for a session.

        Args:
            project_cwd: Project working directory (used as lookup key)
            session_id: Session ID to get path for

        Returns:
            Path to the session file if found, None otherwise
        """
        ...

    # --- Settings operations ---

    @abstractmethod
    def get_settings_path(self) -> Path:
        """Return path to global Claude settings file (~/.claude/settings.json)."""
        ...

    @abstractmethod
    def get_local_settings_path(self) -> Path:
        """Return path to local Claude settings file (~/.claude/settings.local.json)."""
        ...

    @abstractmethod
    def settings_exists(self) -> bool:
        """Check if global settings file exists."""
        ...

    @abstractmethod
    def read_settings(self) -> dict:
        """Read and parse global Claude settings.

        Returns:
            Parsed JSON as dict, or empty dict if file doesn't exist or is invalid
        """
        ...

    # --- Plan operations ---

    @abstractmethod
    def get_plans_dir_path(self) -> Path:
        """Return path to ~/.claude/plans/ directory."""
        ...

    @abstractmethod
    def find_plan_for_session(self, project_cwd: Path, session_id: str) -> Path | None:
        """Find plan file path for session using slug lookup.

        Searches session logs for slug entries and returns the corresponding
        plan file path if found.

        Args:
            project_cwd: Project working directory (for session lookup hint)
            session_id: Session ID to search for plan slugs

        Returns:
            Path to plan file if found, None otherwise
        """
        ...

    @abstractmethod
    def extract_slugs_from_session(self, project_cwd: Path, session_id: str) -> list[str]:
        """Extract plan slugs from session log entries.

        Searches session logs for entries with the given session ID
        and collects any slug fields found. Slugs indicate plan mode
        was entered and correspond to plan filenames.

        Args:
            project_cwd: Project working directory (for session lookup hint)
            session_id: The session ID to search for

        Returns:
            List of slugs in occurrence order (last = most recent)
        """
        ...

    @abstractmethod
    def extract_planning_agent_ids(self, project_cwd: Path, session_id: str) -> list[str]:
        """Extract agent IDs for Task invocations with subagent_type='Plan'.

        Searches session logs for Task tool invocations where subagent_type is "Plan",
        then correlates with tool_result entries to extract the agentId.

        Args:
            project_cwd: Project working directory (for session lookup hint)
            session_id: The session ID to search for

        Returns:
            List of agent IDs in format ["agent-<id>", ...]
        """
        ...

    # --- Projects directory operations ---

    @abstractmethod
    def write_settings(self, settings: dict) -> Path | None:
        """Write settings to ~/.claude/settings.json with backup.

        Creates a backup of existing file before writing.

        Args:
            settings: Settings dict to write

        Returns:
            Path to backup file if created, None if no backup was needed
            (file didn't exist).
        """
        ...

    @abstractmethod
    def projects_dir_exists(self) -> bool:
        """Check if ~/.claude/projects/ directory exists."""
        ...

    @abstractmethod
    def get_projects_dir_path(self) -> Path:
        """Return path to ~/.claude/projects/ directory."""
        ...
