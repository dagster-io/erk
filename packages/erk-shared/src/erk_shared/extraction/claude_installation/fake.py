"""In-memory fake implementation of ClaudeInstallation for testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from erk_shared.extraction.claude_installation.abc import (
    ClaudeInstallation,
    Session,
    SessionContent,
    SessionNotFound,
)


@dataclass(frozen=True)
class FakeSessionData:
    """Test data for a fake session."""

    content: str  # Raw JSONL
    size_bytes: int
    modified_at: float
    agent_logs: dict[str, str] | None = None  # agent_id -> JSONL content
    parent_session_id: str | None = None  # For agent sessions


@dataclass
class FakeProject:
    """Test data for a fake project."""

    sessions: dict[str, FakeSessionData] = field(default_factory=dict)


class FakeClaudeInstallation(ClaudeInstallation):
    """In-memory fake for testing.

    Enables fast, deterministic testing without filesystem I/O.
    Test setup is declarative via constructor parameters.
    """

    def __init__(
        self,
        *,
        projects: dict[Path, FakeProject] | None,
        plans: dict[str, str] | None,
        settings: dict | None,
        local_settings: dict | None,
        session_slugs: dict[str, list[str]] | None,
        session_planning_agents: dict[str, list[str]] | None,
        plans_dir_path: Path | None,
        projects_dir_path: Path | None,
    ) -> None:
        """Initialize fake installation with test data.

        Args:
            projects: Map of project_cwd -> FakeProject with session data
            plans: Map of slug -> plan content for fake plan data
            settings: Global settings dict, or None if file doesn't exist
            local_settings: Local settings dict, or None if file doesn't exist
            session_slugs: Map of session_id -> list of slugs for that session
            session_planning_agents: Map of session_id -> list of agent IDs for Plan agents
            plans_dir_path: Custom path for plans directory (for filesystem tests)
            projects_dir_path: Custom path for projects directory (for filesystem tests)
        """
        self._projects = projects or {}
        self._plans = plans or {}
        self._settings = settings  # None = file doesn't exist
        self._local_settings = local_settings
        self._session_slugs = session_slugs or {}
        self._session_planning_agents = session_planning_agents or {}
        self._plans_dir_path = plans_dir_path
        self._projects_dir_path = projects_dir_path
        self._settings_writes: list[dict] = []

    @classmethod
    def for_test(
        cls,
        *,
        projects: dict[Path, FakeProject] | None = None,
        plans: dict[str, str] | None = None,
        settings: dict | None = None,
        local_settings: dict | None = None,
        session_slugs: dict[str, list[str]] | None = None,
        session_planning_agents: dict[str, list[str]] | None = None,
        plans_dir_path: Path | None = None,
        projects_dir_path: Path | None = None,
    ) -> FakeClaudeInstallation:
        """Create FakeClaudeInstallation with test-friendly defaults.

        All parameters default to None, allowing tests to specify only what they need.
        """
        return cls(
            projects=projects,
            plans=plans,
            settings=settings,
            local_settings=local_settings,
            session_slugs=session_slugs,
            session_planning_agents=session_planning_agents,
            plans_dir_path=plans_dir_path,
            projects_dir_path=projects_dir_path,
        )

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

    # --- Session operations ---

    def has_project(self, project_cwd: Path) -> bool:
        """Check if project exists at or above the given path."""
        return self._find_project_for_path(project_cwd) is not None

    def find_sessions(
        self,
        project_cwd: Path,
        *,
        current_session_id: str | None,
        min_size: int,
        limit: int,
        include_agents: bool,
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
            # Check if this is an agent session (has parent_session_id)
            is_agent = data.parent_session_id is not None

            # Skip agent sessions unless include_agents is True
            if is_agent and not include_agents:
                continue

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
                    is_current=(session_id == current_session_id),
                    parent_session_id=data.parent_session_id,
                )
            )

        return sessions

    def read_session(
        self,
        project_cwd: Path,
        session_id: str,
        *,
        include_agents: bool,
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
        session_id: str | None,
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

    def get_session(
        self,
        project_cwd: Path,
        session_id: str,
    ) -> Session | SessionNotFound:
        """Get a specific session by ID from fake data."""
        project_path = self._find_project_for_path(project_cwd)
        if project_path is None:
            return SessionNotFound(session_id)

        project = self._projects[project_path]
        if session_id not in project.sessions:
            return SessionNotFound(session_id)

        data = project.sessions[session_id]
        return Session(
            session_id=session_id,
            size_bytes=data.size_bytes,
            modified_at=data.modified_at,
            is_current=False,  # show command doesn't track current
            parent_session_id=data.parent_session_id,
        )

    def get_session_path(
        self,
        project_cwd: Path,
        session_id: str,
    ) -> Path | None:
        """Get the file path for a session from fake data.

        Returns a synthetic path for testing purposes.
        """
        project_path = self._find_project_for_path(project_cwd)
        if project_path is None:
            return None

        project = self._projects[project_path]
        if session_id not in project.sessions:
            return None

        # Return synthetic path for testing
        return project_path / f"{session_id}.jsonl"

    # --- Settings operations ---

    def get_settings_path(self) -> Path:
        """Return path to global Claude settings file (fake path)."""
        return Path("/fake/.claude/settings.json")

    def get_local_settings_path(self) -> Path:
        """Return path to local Claude settings file (fake path)."""
        return Path("/fake/.claude/settings.local.json")

    def settings_exists(self) -> bool:
        """Check if global settings file exists."""
        return self._settings is not None

    def read_settings(self) -> dict:
        """Read and parse global Claude settings.

        Returns:
            Parsed JSON as dict, or empty dict if file doesn't exist
        """
        if self._settings is None:
            return {}
        return dict(self._settings)  # Return copy

    def write_settings(self, settings: dict) -> Path | None:
        """Write settings to in-memory storage.

        Does not create actual backups - just stores the new settings.

        Args:
            settings: Settings dict to store

        Returns:
            None (fake never creates real backups)
        """
        self._settings = dict(settings)  # Store a copy
        # Track write for test assertions
        self._settings_writes.append(dict(settings))
        # Return None since fake doesn't create backup files
        return None

    @property
    def settings_writes(self) -> list[dict]:
        """Read-only access to all settings writes for test assertions.

        Returns:
            List of settings dicts that were written, in order
        """
        return list(self._settings_writes)

    # --- Plan operations ---

    def get_plans_dir_path(self) -> Path:
        """Return path to ~/.claude/plans/ directory.

        Returns custom path if configured, otherwise a fake path.
        """
        if self._plans_dir_path is not None:
            return self._plans_dir_path
        return Path("/fake/.claude/plans")

    def extract_slugs_from_session(self, project_cwd: Path, session_id: str) -> list[str]:
        """Extract plan slugs from fake session data.

        Args:
            project_cwd: Project working directory (unused in fake)
            session_id: The session ID to look up

        Returns:
            List of slugs configured for this session, or empty list
        """
        _ = project_cwd  # Unused in fake
        return list(self._session_slugs.get(session_id, []))

    def extract_planning_agent_ids(self, project_cwd: Path, session_id: str) -> list[str]:
        """Extract agent IDs from fake session data.

        Args:
            project_cwd: Project working directory (unused in fake)
            session_id: The session ID to look up

        Returns:
            List of agent IDs configured for this session, or empty list
        """
        _ = project_cwd  # Unused in fake
        return list(self._session_planning_agents.get(session_id, []))

    def find_plan_for_session(self, project_cwd: Path, session_id: str) -> Path | None:
        """Find plan file path from fake session data.

        Args:
            project_cwd: Project working directory (unused in fake)
            session_id: Session ID to search for plan slugs

        Returns:
            Synthetic path to plan file if session has slugs and matching plan exists,
            None otherwise
        """
        slugs = self.extract_slugs_from_session(project_cwd, session_id)
        if not slugs:
            return None

        # Use most recent slug (last in list)
        slug = slugs[-1]

        # Check if we have this plan configured
        if slug not in self._plans:
            return None

        return self.get_plans_dir_path() / f"{slug}.md"

    # --- Projects directory operations ---

    def projects_dir_exists(self) -> bool:
        """Check if projects directory exists.

        If a custom projects_dir_path is set, checks if that path exists.
        Otherwise returns True if any projects are configured.
        """
        if self._projects_dir_path is not None:
            return self._projects_dir_path.exists()
        return len(self._projects) > 0

    def get_projects_dir_path(self) -> Path:
        """Return path to projects directory.

        Returns custom path if configured, otherwise a fake path.
        """
        if self._projects_dir_path is not None:
            return self._projects_dir_path
        return Path("/fake/.claude/projects")
