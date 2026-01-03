"""Production implementation of ClaudeInstallation using local filesystem."""

import json
from pathlib import Path

from erk_shared.extraction.claude_installation.abc import (
    ClaudeInstallation,
    Session,
    SessionContent,
    SessionNotFound,
)
from erk_shared.extraction.session_schema import (
    extract_agent_id_from_tool_result,
    extract_task_tool_use_id,
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
        if not self.plans_dir_exists():
            return None

        # Session-scoped lookup via slug extraction
        if session_id is not None:
            slugs = self.extract_slugs_from_session(session_id, cwd_hint=project_cwd)
            if slugs:
                # Use most recent slug (last in list)
                slug = slugs[-1]
                plan_file = self.find_plan_by_slug(slug)
                if plan_file is not None:
                    return plan_file.read_text(encoding="utf-8")

        # Fallback: mtime-based selection
        plan_files = self.list_plan_files()
        if not plan_files:
            return None

        return plan_files[0][0].read_text(encoding="utf-8")

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

    # --- Plans directory operations ---

    def get_plans_dir_path(self) -> Path:
        """Return path to Claude plans directory (~/.claude/plans/)."""
        return Path.home() / ".claude" / "plans"

    def plans_dir_exists(self) -> bool:
        """Check if plans directory exists."""
        return self.get_plans_dir_path().exists()

    def find_plan_by_slug(self, slug: str) -> Path | None:
        """Find a plan file by its slug."""
        plans_dir = self.get_plans_dir_path()
        if not plans_dir.exists():
            return None
        plan_file = plans_dir / f"{slug}.md"
        if plan_file.exists() and plan_file.is_file():
            return plan_file
        return None

    def list_plan_files(self) -> list[tuple[Path, float]]:
        """List all plan files with their mtimes, sorted newest-first."""
        plans_dir = self.get_plans_dir_path()
        if not plans_dir.exists():
            return []
        plan_files = [(f, f.stat().st_mtime) for f in plans_dir.glob("*.md") if f.is_file()]
        plan_files.sort(key=lambda x: x[1], reverse=True)
        return plan_files

    # --- Session-to-slug correlation ---

    def _iter_session_entries(
        self, project_dir: Path, session_id: str, max_lines: int | None
    ) -> list[dict]:
        """Iterate over JSONL entries matching a session ID in a project directory.

        Args:
            project_dir: Path to project directory
            session_id: Session ID to filter entries by
            max_lines: Optional max lines to read per file (for existence checks)

        Returns:
            List of JSON entries matching the session ID
        """
        entries: list[dict] = []

        for jsonl_file in project_dir.glob("*.jsonl"):
            if jsonl_file.name.startswith("agent-"):
                continue

            with open(jsonl_file, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if max_lines is not None and i >= max_lines:
                        break
                    stripped = line.strip()
                    if not stripped:
                        continue
                    entry = json.loads(stripped)
                    if entry.get("sessionId") == session_id:
                        entries.append(entry)

        return entries

    def _check_session_in_project(self, project_dir: Path, session_id: str) -> bool:
        """Check if a session ID exists in a project directory."""
        entries = self._iter_session_entries(project_dir, session_id, max_lines=10)
        return len(entries) > 0

    def _find_project_dir_for_session(self, session_id: str, cwd_hint: Path | None) -> Path | None:
        """Find the project directory containing logs for a session ID.

        Uses cwd_hint for O(1) lookup when available. Falls back to scanning
        all project directories if hint not provided or doesn't match.
        """
        projects_dir = self.get_projects_dir_path()
        if not projects_dir.exists():
            return None

        # Fast path: use cwd hint to directly compute project directory
        if cwd_hint is not None:
            encoded = self.encode_path_to_project_folder(cwd_hint)
            hint_project_dir = projects_dir / encoded
            if hint_project_dir.exists() and hint_project_dir.is_dir():
                if self._check_session_in_project(hint_project_dir, session_id):
                    return hint_project_dir

        # Slow path: scan all project directories
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            if self._check_session_in_project(project_dir, session_id):
                return project_dir

        return None

    def extract_slugs_from_session(self, session_id: str, cwd_hint: Path | None) -> list[str]:
        """Extract plan slugs from session log entries."""
        project_dir = self._find_project_dir_for_session(session_id, cwd_hint=cwd_hint)
        if project_dir is None:
            return []

        # Read all entries (no line limit) and extract unique slugs
        entries = self._iter_session_entries(project_dir, session_id, max_lines=None)

        slugs: list[str] = []
        seen_slugs: set[str] = set()

        for entry in entries:
            slug = entry.get("slug")
            if slug and slug not in seen_slugs:
                slugs.append(slug)
                seen_slugs.add(slug)

        return slugs

    def extract_planning_agent_ids(self, session_id: str, cwd_hint: Path | None) -> list[str]:
        """Extract agent IDs for Task invocations with subagent_type='Plan'."""
        project_dir = self._find_project_dir_for_session(session_id, cwd_hint=cwd_hint)
        if project_dir is None:
            return []

        # Read all entries for this session
        entries = self._iter_session_entries(project_dir, session_id, max_lines=None)

        # Step 1: Collect Task tool_use entries with subagent_type="Plan"
        plan_task_ids: set[str] = set()

        # Step 2: Collect tool_result entries: tool_use_id -> agentId
        tool_to_agent: dict[str, str] = {}

        for entry in entries:
            entry_type = entry.get("type")

            if entry_type == "assistant":
                tool_use_id = extract_task_tool_use_id(entry, subagent_type="Plan")
                if tool_use_id is not None:
                    plan_task_ids.add(tool_use_id)

            elif entry_type == "user":
                result = extract_agent_id_from_tool_result(entry)
                if result is not None:
                    tool_use_id, agent_id = result
                    tool_to_agent[tool_use_id] = agent_id

        # Step 3: Match Plan Task IDs with their agent IDs
        agent_ids: list[str] = []
        for tool_use_id in plan_task_ids:
            agent_id = tool_to_agent.get(tool_use_id)
            if agent_id:
                agent_ids.append(f"agent-{agent_id}")

        return agent_ids

    # --- Projects directory operations ---

    def get_projects_dir_path(self) -> Path:
        """Return path to Claude projects directory (~/.claude/projects/)."""
        return Path.home() / ".claude" / "projects"

    def projects_dir_exists(self) -> bool:
        """Check if projects directory exists."""
        return self.get_projects_dir_path().exists()

    def encode_path_to_project_folder(self, path: Path) -> str:
        """Encode filesystem path to Claude project folder name."""
        return str(path).replace("/", "-").replace(".", "-")

    def find_project_info(self, path: Path) -> tuple[Path, list[str], str | None] | None:
        """Find project directory, session logs, and latest session ID for a path."""
        projects_dir = self.get_projects_dir_path()
        if not projects_dir.exists():
            return None

        encoded_path = self.encode_path_to_project_folder(path)
        project_dir = projects_dir / encoded_path

        if not project_dir.exists():
            return None

        # Find all session logs
        session_logs: list[str] = []
        latest_session: tuple[str, float] | None = None

        for log_file in project_dir.iterdir():
            if log_file.is_file() and log_file.suffix == ".jsonl":
                session_logs.append(log_file.name)

                # Track latest main session (not agent logs)
                if not log_file.name.startswith("agent-"):
                    mtime = log_file.stat().st_mtime
                    if latest_session is None or mtime > latest_session[1]:
                        session_id = log_file.stem
                        latest_session = (session_id, mtime)

        # Sort logs for consistent output
        session_logs.sort()

        latest_session_id = latest_session[0] if latest_session else None
        return (project_dir, session_logs, latest_session_id)
