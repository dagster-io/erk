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
        plans_dir = self.get_plans_dir_path()
        if not plans_dir.exists():
            return None

        # Session-scoped lookup via slug extraction
        if session_id:
            plan_file = self.find_plan_for_session(project_cwd, session_id)
            if plan_file is not None:
                return plan_file.read_text(encoding="utf-8")

        # Fallback: mtime-based selection
        plan_files = sorted(
            [f for f in plans_dir.glob("*.md") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        if not plan_files:
            return None

        return plan_files[0].read_text(encoding="utf-8")

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

    # --- Plan operations ---

    def get_plans_dir_path(self) -> Path:
        """Return path to ~/.claude/plans/ directory."""
        return Path.home() / ".claude" / "plans"

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
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("sessionId") == session_id:
                        entries.append(entry)

        return entries

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
        project_dir = self._get_project_dir(project_cwd)
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
        project_dir = self._get_project_dir(project_cwd)
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
        slugs = self.extract_slugs_from_session(project_cwd, session_id)
        if not slugs:
            return None

        # Use most recent slug (last in list)
        slug = slugs[-1]
        plan_file = self.get_plans_dir_path() / f"{slug}.md"
        if plan_file.exists() and plan_file.is_file():
            return plan_file

        return None

    def write_settings(self, settings: dict) -> Path | None:
        """Write settings to ~/.claude/settings.json with backup.

        Creates a backup of existing file before writing.

        Args:
            settings: Settings dict to write

        Returns:
            Path to backup file if created, None if no backup was needed
            (file didn't exist).
        """
        path = self.get_settings_path()

        # Create backup of existing file (if it exists)
        backup_path: Path | None = None
        if path.exists():
            backup_path = path.with_suffix(".json.bak")
            backup_path.write_bytes(path.read_bytes())

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write with pretty formatting to match Claude's style
        content = json.dumps(settings, indent=2)
        path.write_text(content, encoding="utf-8")

        return backup_path

    # --- Projects directory operations ---

    def projects_dir_exists(self) -> bool:
        """Check if ~/.claude/projects/ directory exists."""
        return self.get_projects_dir_path().exists()

    def get_projects_dir_path(self) -> Path:
        """Return path to ~/.claude/projects/ directory."""
        return Path.home() / ".claude" / "projects"
