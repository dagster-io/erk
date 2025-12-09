"""In-memory fake implementation of SessionStore for testing."""

from dataclasses import dataclass, field
from pathlib import Path

from erk_shared.extraction.claude_code_session_store.abc import (
    ClaudeCodeSessionStore,
    Session,
    SessionContent,
)


@dataclass
class FakeSessionData:
    """Test data for a fake session."""

    content: str  # Raw JSONL
    size_bytes: int
    modified_at: float
    agent_logs: dict[str, str] | None = None  # agent_id -> JSONL content


@dataclass
class FakeProject:
    """Test data for a fake project."""

    sessions: dict[str, FakeSessionData] = field(default_factory=dict)


class FakeClaudeCodeSessionStore(ClaudeCodeSessionStore):
    """In-memory fake for testing.

    Enables fast, deterministic testing without filesystem I/O.
    Test setup is declarative via constructor parameters.
    """

    def __init__(
        self,
        *,
        current_session_id: str | None = None,
        projects: dict[Path, FakeProject] | None = None,
        plans: dict[str, str] | None = None,
    ) -> None:
        """Initialize fake store with test data.

        Args:
            current_session_id: Simulated current session ID
            projects: Map of project_cwd -> FakeProject with session data
            plans: Map of slug -> plan content for fake plan data
        """
        self._current_session_id = current_session_id
        self._projects = projects or {}
        self._plans = plans or {}

    def get_current_session_id(self) -> str | None:
        """Return the configured current session ID."""
        return self._current_session_id

    def _find_project_for_path(self, project_cwd: Path) -> Path | None:
        """Find project at or above the given path.

        Walks up the directory tree to find a matching project.
        """
        current = project_cwd.resolve()

        while True:
            if current in self._projects:
                return current

            parent = current.parent
            if parent == current:  # Hit filesystem root
                break
            current = parent

        return None

    def has_project(self, project_cwd: Path) -> bool:
        """Check if project exists at or above the given path."""
        return self._find_project_for_path(project_cwd) is not None

    def find_sessions(
        self,
        project_cwd: Path,
        *,
        min_size: int = 0,
        limit: int = 10,
    ) -> list[Session]:
        """Find sessions from fake project data.

        Returns sessions sorted by modified_at descending (newest first).
        """
        project_path = self._find_project_for_path(project_cwd)
        if project_path is None:
            return []

        project = self._projects[project_path]

        # Filter and collect sessions
        session_list: list[tuple[str, FakeSessionData]] = []
        for session_id, data in project.sessions.items():
            if min_size > 0 and data.size_bytes < min_size:
                continue
            session_list.append((session_id, data))

        # Sort by modified_at descending
        session_list.sort(key=lambda x: x[1].modified_at, reverse=True)

        # Build Session objects
        sessions: list[Session] = []
        for session_id, data in session_list[:limit]:
            sessions.append(
                Session(
                    session_id=session_id,
                    size_bytes=data.size_bytes,
                    modified_at=data.modified_at,
                    is_current=(session_id == self._current_session_id),
                )
            )

        return sessions

    def read_session(
        self,
        project_cwd: Path,
        session_id: str,
        *,
        include_agents: bool = True,
    ) -> SessionContent | None:
        """Read session content from fake data."""
        project_path = self._find_project_for_path(project_cwd)
        if project_path is None:
            return None

        project = self._projects[project_path]
        if session_id not in project.sessions:
            return None

        session_data = project.sessions[session_id]

        agent_logs: list[tuple[str, str]] = []
        if include_agents and session_data.agent_logs:
            # Sort agent logs by ID for deterministic order
            for agent_id in sorted(session_data.agent_logs.keys()):
                agent_logs.append((agent_id, session_data.agent_logs[agent_id]))

        return SessionContent(
            main_content=session_data.content,
            agent_logs=agent_logs,
        )

    def get_latest_plan(
        self,
        project_cwd: Path,
        *,
        session_id: str | None = None,
    ) -> str | None:
        """Return fake plan content.

        If session_id matches a key in _plans, returns that plan.
        Otherwise returns the first plan (simulating most-recent by mtime).

        Args:
            project_cwd: Project working directory (unused in fake)
            session_id: Optional session ID for session-scoped lookup

        Returns:
            Plan content as markdown string, or None if no plans configured
        """
        _ = project_cwd  # Unused in fake

        # If session_id provided and matches a plan slug, return it
        if session_id and session_id in self._plans:
            return self._plans[session_id]

        # Fall back to first plan (simulating most recent by mtime)
        if self._plans:
            return next(iter(self._plans.values()))

        return None
