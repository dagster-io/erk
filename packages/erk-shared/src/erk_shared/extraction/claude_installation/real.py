"""Production implementation of ClaudeInstallation using local filesystem."""

import json
from pathlib import Path

from erk_shared.extraction.claude_installation.abc import (
    ClaudeInstallation,
    Session,
    SessionContent,
    SessionNotFound,
)


def _extract_parent_session_id(agent_log_path: Path) -> str | None:
    """Extract the parent sessionId from an agent log file.

    Reads the first few lines of the agent log to find a JSON object
    with a sessionId field.

    Args:
        agent_log_path: Path to the agent log file

    Returns:
        Parent session ID if found, None otherwise
    """
    content = agent_log_path.read_text(encoding="utf-8")
    for line in content.split("\n")[:10]:  # Check first 10 lines
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        entry = json.loads(stripped)
        if "sessionId" in entry:
            return entry["sessionId"]
    return None


class RealClaudeInstallation(ClaudeInstallation):
    """Production implementation using local filesystem.

    Reads sessions from ~/.claude/projects/ directory structure.
    Reads settings from ~/.claude/settings.json.
    """

    def _get_project_dir(self, project_cwd: Path) -> Path | None:
        """Internal: Map cwd to Claude Code project directory.

        First checks exact match, then walks up the directory tree
        to find parent directories that have Claude projects.

        Args:
            project_cwd: Working directory to look up

        Returns:
            Path to project directory if found, None otherwise
        """
        projects_dir = Path.home() / ".claude" / "projects"
        if not projects_dir.exists():
            return None

        current = project_cwd.resolve()

        while True:
            # Encode path using Claude Code's scheme
            encoded = str(current).replace("/", "-").replace(".", "-")
            project_dir = projects_dir / encoded

            if project_dir.exists():
                return project_dir

            parent = current.parent
            if parent == current:  # Hit filesystem root
                break
            current = parent

        return None

    # --- Session operations ---

    def has_project(self, project_cwd: Path) -> bool:
        """Check if a Claude Code project exists for the given working directory."""
        return self._get_project_dir(project_cwd) is not None

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

        Returns sessions sorted by modified_at descending (newest first).
        """
        project_dir = self._get_project_dir(project_cwd)
        if project_dir is None:
            return []

        # Collect session files (session_id, mtime, size, parent_session_id)
        session_files: list[tuple[str, float, int, str | None]] = []
        for log_file in project_dir.iterdir():
            if not log_file.is_file():
                continue
            if log_file.suffix != ".jsonl":
                continue

            is_agent = log_file.name.startswith("agent-")

            # Skip agent files unless include_agents is True
            if is_agent and not include_agents:
                continue

            stat = log_file.stat()
            mtime = stat.st_mtime
            size = stat.st_size

            # Filter by minimum size
            if min_size > 0 and size < min_size:
                continue

            session_id = log_file.stem
            parent_session_id: str | None = None

            if is_agent:
                parent_session_id = _extract_parent_session_id(log_file)

            session_files.append((session_id, mtime, size, parent_session_id))

        # Sort by mtime descending (newest first)
        session_files.sort(key=lambda x: x[1], reverse=True)

        # Build Session objects
        sessions: list[Session] = []
        for session_id, mtime, size, parent_session_id in session_files[:limit]:
            sessions.append(
                Session(
                    session_id=session_id,
                    size_bytes=size,
                    modified_at=mtime,
                    is_current=(session_id == current_session_id),
                    parent_session_id=parent_session_id,
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
        """Read raw session content.

        Returns raw JSONL strings without preprocessing.
        """
        project_dir = self._get_project_dir(project_cwd)
        if project_dir is None:
            return None

        session_file = project_dir / f"{session_id}.jsonl"
        if not session_file.exists():
            return None

        # Read main session content
        main_content = session_file.read_text(encoding="utf-8")

        # Discover and read agent logs
        agent_logs: list[tuple[str, str]] = []
        if include_agents:
            for agent_file in sorted(project_dir.glob("agent-*.jsonl")):
                agent_id = agent_file.stem.replace("agent-", "")
                agent_content = agent_file.read_text(encoding="utf-8")
                agent_logs.append((agent_id, agent_content))

        return SessionContent(
            main_content=main_content,
            agent_logs=agent_logs,
        )

    def get_latest_plan(
        self,
        project_cwd: Path,
        *,
        session_id: str | None,
    ) -> str | None:
        """Get latest plan from ~/.claude/plans/.

        Args:
            project_cwd: Project working directory (used as hint for session lookup)
            session_id: Optional session ID for session-scoped lookup

        Returns:
            Plan content as markdown string, or None if no plan found
        """
        from erk_shared.extraction.local_plans import get_latest_plan_content

        # Note: project_cwd could be used for session correlation in future
        _ = project_cwd
        return get_latest_plan_content(session_id=session_id)

    def get_session(
        self,
        project_cwd: Path,
        session_id: str,
    ) -> Session | SessionNotFound:
        """Get a specific session by ID.

        Searches through all sessions (including agents) to find the matching ID.
        """
        project_dir = self._get_project_dir(project_cwd)
        if project_dir is None:
            return SessionNotFound(session_id)

        # Check if it's an agent session
        is_agent = session_id.startswith("agent-")

        # Build the expected path
        session_file = project_dir / f"{session_id}.jsonl"
        if not session_file.exists():
            return SessionNotFound(session_id)

        stat = session_file.stat()

        # For agent sessions, extract parent_session_id
        parent_session_id: str | None = None
        if is_agent:
            parent_session_id = _extract_parent_session_id(session_file)

        return Session(
            session_id=session_id,
            size_bytes=stat.st_size,
            modified_at=stat.st_mtime,
            is_current=False,  # show command doesn't track current
            parent_session_id=parent_session_id,
        )

    def get_session_path(
        self,
        project_cwd: Path,
        session_id: str,
    ) -> Path | None:
        """Get the file path for a session."""
        project_dir = self._get_project_dir(project_cwd)
        if project_dir is None:
            return None

        session_file = project_dir / f"{session_id}.jsonl"
        if not session_file.exists():
            return None

        return session_file

    # --- Settings operations ---

    def get_settings_path(self) -> Path:
        """Return path to global Claude settings file (~/.claude/settings.json)."""
        return Path.home() / ".claude" / "settings.json"

    def get_local_settings_path(self) -> Path:
        """Return path to local Claude settings file (~/.claude/settings.local.json)."""
        return Path.home() / ".claude" / "settings.local.json"

    def settings_exists(self) -> bool:
        """Check if global settings file exists."""
        return self.get_settings_path().exists()

    def read_settings(self) -> dict:
        """Read and parse global Claude settings.

        Returns:
            Parsed JSON as dict, or empty dict if file doesn't exist or is invalid
        """
        path = self.get_settings_path()
        if not path.exists():
            return {}
        content = path.read_text(encoding="utf-8")
        return json.loads(content)
