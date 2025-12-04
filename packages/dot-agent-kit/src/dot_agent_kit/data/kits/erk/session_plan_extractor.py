"""Extract implementation plans from Claude plans directory.

This module provides functionality to extract plans from ~/.claude/plans/.
Plans are stored as {slug}.md files. When a session_id is provided, we parse
session logs to find the slug associated with that session. Otherwise, we
return the most recently modified plan file.

All functions follow LBYL (Look Before You Leap) patterns and handle
errors explicitly at boundaries.
"""

import json
import os
from pathlib import Path


def find_project_dir_for_session(session_id: str) -> Path | None:
    """Find the project directory containing logs for a session ID.

    Searches ~/.claude/projects/ directories for session logs
    matching the given session ID. Only checks the first 10 lines
    of each JSONL file to quickly match sessions.

    Args:
        session_id: The session ID to search for

    Returns:
        Path to the project directory if found, None otherwise
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        for jsonl_file in project_dir.glob("*.jsonl"):
            # Skip agent session files
            if jsonl_file.name.startswith("agent-"):
                continue

            # Check first 10 lines for session ID match
            try:
                with open(jsonl_file, encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        if i >= 10:
                            break
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if entry.get("sessionId") == session_id:
                                return project_dir
                        except json.JSONDecodeError:
                            continue
            except OSError:
                # Skip files we can't read
                continue

    return None


def extract_slugs_from_session(session_id: str) -> list[str]:
    """Extract plan slugs from session log entries.

    Searches session logs for entries with the given session ID
    and collects any slug fields found. Slugs indicate plan mode
    was entered and correspond to plan filenames.

    Args:
        session_id: The session ID to search for

    Returns:
        List of slugs in occurrence order (last = most recent)
    """
    project_dir = find_project_dir_for_session(session_id)
    if not project_dir:
        return []

    slugs: list[str] = []
    seen_slugs: set[str] = set()

    for jsonl_file in project_dir.glob("*.jsonl"):
        # Skip agent session files
        if jsonl_file.name.startswith("agent-"):
            continue

        try:
            with open(jsonl_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        # Only collect slugs from entries matching our session
                        if entry.get("sessionId") != session_id:
                            continue
                        slug = entry.get("slug")
                        if slug and slug not in seen_slugs:
                            slugs.append(slug)
                            seen_slugs.add(slug)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            # Skip files we can't read
            continue

    return slugs


def get_plans_dir() -> Path:
    """Return the Claude plans directory path.

    Returns:
        Path to ~/.claude/plans/
    """
    return Path.home() / ".claude" / "plans"


def get_latest_plan(working_dir: str, session_id: str | None = None) -> str | None:
    """Get plan from ~/.claude/plans/, optionally scoped to a session.

    When session_id is provided, searches session logs for a slug field
    that matches a plan filename. Falls back to most recent plan by mtime
    when no session-specific plan is found.

    Args:
        working_dir: Current working directory (unused, kept for API compatibility)
        session_id: Optional session ID for session-scoped lookup

    Returns:
        Plan text as markdown string, or None if no plan found
    """
    # Silence unused parameter warning
    _ = working_dir

    plans_dir = get_plans_dir()

    if not plans_dir.exists():
        return None

    # If session_id provided, try to find session-specific plan via slug
    if session_id:
        slugs = extract_slugs_from_session(session_id)
        if slugs:
            # Use most recent slug (last in list)
            slug = slugs[-1]
            plan_file = plans_dir / f"{slug}.md"
            if plan_file.exists() and plan_file.is_file():
                return plan_file.read_text(encoding="utf-8")

    # Fallback: mtime-based selection (current behavior)
    plan_files = sorted(
        [f for f in plans_dir.glob("*.md") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if not plan_files:
        return None

    return plan_files[0].read_text(encoding="utf-8")


def get_session_context() -> str | None:
    """Extract current session ID from environment if available.

    Claude Code sets SESSION_CONTEXT with format: session_id=<uuid>
    Also checks CLAUDE_SESSION_ID for backward compatibility.

    Returns:
        Session ID string or None if not in a Claude session
    """
    # Check for SESSION_CONTEXT (Claude Code format: session_id=<uuid>)
    session_context = os.environ.get("SESSION_CONTEXT")
    if session_context and "session_id=" in session_context:
        # Extract session_id from "session_id=<uuid>" format
        parts = session_context.split("session_id=")
        if len(parts) > 1:
            session_id = parts[1].strip()
            if session_id:
                return session_id

    # Check for CLAUDE_SESSION_ID (legacy format)
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if session_id:
        return session_id

    # Not in a Claude session
    return None
