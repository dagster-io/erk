"""Production implementation of SessionStore using local filesystem."""

import os
from pathlib import Path

from erk_shared.extraction.claude_code_session_store.abc import (
    ClaudeCodeSessionStore,
    Session,
    SessionContent,
)


class RealClaudeCodeSessionStore(ClaudeCodeSessionStore):
    """Production implementation using local filesystem.

    Reads sessions from ~/.claude/projects/ directory structure.
    """

    def get_current_session_id(self) -> str | None:
        """Extract current session ID from SESSION_CONTEXT environment variable.

        The SESSION_CONTEXT env var contains: session_id=<uuid>

        Returns:
            Session ID string or None if not found
        """
        ctx = os.environ.get("SESSION_CONTEXT", "")
        if "session_id=" in ctx:
            return ctx.split("session_id=")[1].strip()
        return None

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

    def has_project(self, project_cwd: Path) -> bool:
        """Check if a Claude Code project exists for the given working directory."""
        return self._get_project_dir(project_cwd) is not None

    def find_sessions(
        self,
        project_cwd: Path,
        *,
        min_size: int = 0,
        limit: int = 10,
    ) -> list[Session]:
        """Find sessions for a project.

        Returns sessions sorted by modified_at descending (newest first).
        """
        project_dir = self._get_project_dir(project_cwd)
        if project_dir is None:
            return []

        current_session_id = self.get_current_session_id()

        # Collect session files (exclude agent logs)
        session_files: list[tuple[str, float, int]] = []
        for log_file in project_dir.iterdir():
            if not log_file.is_file():
                continue
            if log_file.suffix != ".jsonl":
                continue
            if log_file.name.startswith("agent-"):
                continue

            stat = log_file.stat()
            mtime = stat.st_mtime
            size = stat.st_size

            # Filter by minimum size
            if min_size > 0 and size < min_size:
                continue

            session_id = log_file.stem
            session_files.append((session_id, mtime, size))

        # Sort by mtime descending (newest first)
        session_files.sort(key=lambda x: x[1], reverse=True)

        # Build Session objects
        sessions: list[Session] = []
        for session_id, mtime, size in session_files[:limit]:
            sessions.append(
                Session(
                    session_id=session_id,
                    size_bytes=size,
                    modified_at=mtime,
                    is_current=(session_id == current_session_id),
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
        session_id: str | None = None,
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
