"""Local plan extraction from ~/.claude/plans/.

This module provides the core plan extraction logic for ClaudeCodeSessionStore.
It extracts plans from the Claude plans directory, supporting both mtime-based
selection and session-scoped lookup via slugs.
"""

import json
from pathlib import Path

from erk_shared.extraction.session_schema import (
    extract_agent_id_from_tool_result,
    extract_task_tool_use_id,
)


def get_plans_dir() -> Path:
    """Return the Claude plans directory path.

    Returns:
        Path to ~/.claude/plans/
    """
    return Path.home() / ".claude" / "plans"


def _encode_path_to_project_folder(path: str) -> str:
    """Encode a filesystem path to Claude project folder name.

    Applies deterministic encoding: prepend '-', replace '/' and '.' with '-'.

    Args:
        path: Absolute filesystem path

    Returns:
        Encoded project folder name
    """
    return "-" + path.replace("/", "-").replace(".", "-").lstrip("-")


def _iter_session_entries(
    project_dir: Path, session_id: str, *, max_lines: int | None = None
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


def _check_session_in_project(project_dir: Path, session_id: str) -> bool:
    """Check if a session ID exists in a project directory.

    Args:
        project_dir: Path to project directory
        session_id: Session ID to search for

    Returns:
        True if session found, False otherwise
    """
    # Only need to check first 10 lines per file for existence
    entries = _iter_session_entries(project_dir, session_id, max_lines=10)
    return len(entries) > 0


def find_project_dir_for_session(session_id: str, cwd_hint: str | None = None) -> Path | None:
    """Find the project directory containing logs for a session ID.

    Uses cwd_hint for O(1) lookup when available. Falls back to scanning
    all project directories if hint not provided or doesn't match.

    Args:
        session_id: The session ID to search for
        cwd_hint: Optional current working directory as optimization hint

    Returns:
        Path to the project directory if found, None otherwise
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None

    # Fast path: use cwd hint to directly compute project directory
    if cwd_hint:
        encoded = _encode_path_to_project_folder(cwd_hint)
        hint_project_dir = projects_dir / encoded
        if hint_project_dir.exists() and hint_project_dir.is_dir():
            if _check_session_in_project(hint_project_dir, session_id):
                return hint_project_dir

    # Slow path: scan all project directories
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        if _check_session_in_project(project_dir, session_id):
            return project_dir

    return None


def extract_slugs_from_session(session_id: str, cwd_hint: str | None = None) -> list[str]:
    """Extract plan slugs from session log entries.

    Searches session logs for entries with the given session ID
    and collects any slug fields found. Slugs indicate plan mode
    was entered and correspond to plan filenames.

    Args:
        session_id: The session ID to search for
        cwd_hint: Optional current working directory for faster lookup

    Returns:
        List of slugs in occurrence order (last = most recent)
    """
    project_dir = find_project_dir_for_session(session_id, cwd_hint=cwd_hint)
    if not project_dir:
        return []

    # Read all entries (no line limit) and extract unique slugs
    entries = _iter_session_entries(project_dir, session_id)

    slugs: list[str] = []
    seen_slugs: set[str] = set()

    for entry in entries:
        slug = entry.get("slug")
        if slug and slug not in seen_slugs:
            slugs.append(slug)
            seen_slugs.add(slug)

    return slugs


def extract_planning_agent_ids(session_id: str, cwd_hint: str | None) -> list[str]:
    """Extract agent IDs for Task invocations with subagent_type='Plan'.

    Searches session logs for Task tool invocations where subagent_type is "Plan",
    then correlates with tool_result entries to extract the agentId.

    Args:
        session_id: The session ID to search for.
        cwd_hint: Optional current working directory for faster lookup.

    Returns:
        List of agent IDs in format ["agent-<id>", ...].
    """
    project_dir = find_project_dir_for_session(session_id, cwd_hint=cwd_hint)
    if project_dir is None:
        return []

    # Read all entries for this session
    entries = _iter_session_entries(project_dir, session_id)

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


def get_latest_plan_content(session_id: str | None = None) -> str | None:
    """Get plan content from ~/.claude/plans/, optionally session-scoped.

    When session_id is provided, searches session logs for a slug field
    that matches a plan filename. Falls back to most recent plan by mtime
    when no session-specific plan is found.

    Args:
        session_id: Optional session ID for session-scoped lookup

    Returns:
        Plan content as markdown string, or None if no plan found
    """
    plans_dir = get_plans_dir()
    if not plans_dir.exists():
        return None

    # Session-scoped lookup via slug extraction
    if session_id:
        slugs = extract_slugs_from_session(session_id)
        if slugs:
            # Use most recent slug (last in list)
            slug = slugs[-1]
            plan_file = plans_dir / f"{slug}.md"
            if plan_file.exists() and plan_file.is_file():
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
