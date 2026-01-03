"""In-memory fake implementation of ClaudeInstallation for testing."""

import json
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
    ) -> None:
        """Initialize fake installation with test data.

        Args:
            projects: Map of project_cwd -> FakeProject with session data
            plans: Map of slug -> plan content for fake plan data
            settings: Global settings dict, or None if file doesn't exist
            local_settings: Local settings dict, or None if file doesn't exist
        """
        self._projects = projects or {}
        self._plans = plans or {}
        self._settings = settings  # None = file doesn't exist
        self._local_settings = local_settings

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

    # --- Plans directory operations ---

    def get_plans_dir_path(self) -> Path:
        """Return fake path to Claude plans directory."""
        return Path("/fake/.claude/plans")

    def plans_dir_exists(self) -> bool:
        """Check if plans directory exists (True if any plans configured)."""
        return len(self._plans) > 0

    def find_plan_by_slug(self, slug: str) -> Path | None:
        """Find a plan file by its slug from fake data."""
        if slug not in self._plans:
            return None
        # Return synthetic path for testing
        return self.get_plans_dir_path() / f"{slug}.md"

    def list_plan_files(self) -> list[tuple[Path, float]]:
        """List all plan files with synthetic mtimes.

        Returns plans in insertion order with synthetic mtimes.
        """
        plans_dir = self.get_plans_dir_path()
        # Assign synthetic mtimes (first plan = oldest, last = newest)
        plan_list: list[tuple[Path, float]] = []
        for i, slug in enumerate(self._plans.keys()):
            plan_list.append((plans_dir / f"{slug}.md", float(i)))
        # Reverse to return newest-first (like real implementation)
        plan_list.reverse()
        return plan_list

    # --- Session-to-slug correlation ---

    def extract_slugs_from_session(self, session_id: str, cwd_hint: Path | None) -> list[str]:
        """Extract plan slugs from fake session data.

        In fake implementation, returns empty list unless slug data was
        embedded in the session JSONL content.
        """
        _ = cwd_hint  # Not used in fake
        # Search through all projects for this session and extract slugs
        for project in self._projects.values():
            if session_id not in project.sessions:
                continue
            # Parse JSONL content to find slug entries
            session_data = project.sessions[session_id]
            slugs: list[str] = []
            seen_slugs: set[str] = set()
            for line in session_data.content.split("\n"):
                stripped = line.strip()
                if not stripped or not stripped.startswith("{"):
                    continue
                # Parse JSON and look for slug field
                entry = json.loads(stripped)
                if entry.get("sessionId") == session_id:
                    slug = entry.get("slug")
                    if slug and slug not in seen_slugs:
                        slugs.append(slug)
                        seen_slugs.add(slug)
            return slugs
        return []

    def extract_planning_agent_ids(self, session_id: str, cwd_hint: Path | None) -> list[str]:
        """Extract planning agent IDs from fake session data.

        Returns empty list in fake implementation - tests that need
        this should provide appropriate session content.
        """
        _ = session_id
        _ = cwd_hint
        return []

    # --- Projects directory operations ---

    def get_projects_dir_path(self) -> Path:
        """Return fake path to Claude projects directory."""
        return Path("/fake/.claude/projects")

    def projects_dir_exists(self) -> bool:
        """Check if projects directory exists (True if any projects configured)."""
        return len(self._projects) > 0

    def encode_path_to_project_folder(self, path: Path) -> str:
        """Encode filesystem path to Claude project folder name."""
        return str(path).replace("/", "-").replace(".", "-")

    def find_project_info(self, path: Path) -> tuple[Path, list[str], str | None] | None:
        """Find project info from fake data."""
        if path not in self._projects:
            return None

        project = self._projects[path]

        # Build session log names
        session_logs: list[str] = []
        latest_session: tuple[str, float] | None = None

        for session_id, data in project.sessions.items():
            log_name = f"{session_id}.jsonl"
            session_logs.append(log_name)

            # Track latest main session (not agent logs)
            if not session_id.startswith("agent-"):
                if latest_session is None or data.modified_at > latest_session[1]:
                    latest_session = (session_id, data.modified_at)

        session_logs.sort()
        latest_session_id = latest_session[0] if latest_session else None

        # Return synthetic project dir path
        encoded = self.encode_path_to_project_folder(path)
        project_dir = self.get_projects_dir_path() / encoded

        return (project_dir, session_logs, latest_session_id)
