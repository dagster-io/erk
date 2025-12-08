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
    ) -> None:
        """Initialize fake store with test data.

        Args:
            current_session_id: Simulated current session ID
            projects: Map of project_cwd -> FakeProject with session data
        """
        self._current_session_id = current_session_id
        self._projects = projects or {}

    def get_current_session_id(self) -> str | None:
        """Return the configured current session ID."""
        return self._current_session_id

    def has_project(self, project_cwd: Path) -> bool:
        """Check if project exists in fake data."""
        return project_cwd in self._projects

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
        if project_cwd not in self._projects:
            return []

        project = self._projects[project_cwd]

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
        if project_cwd not in self._projects:
            return None

        project = self._projects[project_cwd]
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
