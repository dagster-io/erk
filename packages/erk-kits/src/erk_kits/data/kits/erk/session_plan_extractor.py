"""Extract implementation plans from Claude plans directory.

This module provides functionality to extract plans from ~/.claude/plans/.
Plans are stored as {slug}.md files. When a session_id is provided, we parse
session logs to find the slug associated with that session. Otherwise, we
return the most recently modified plan file.

All functions follow LBYL (Look Before You Leap) patterns and handle
errors explicitly at boundaries.

Note: Core slug extraction logic is in erk_shared.extraction.local_plans.
This module re-exports those functions and adds kit-specific helpers.
"""

import os

# Import from canonical location in erk-shared
from erk_shared.extraction.local_plans import (
    extract_slugs_from_session as extract_slugs_from_session,
)
from erk_shared.extraction.local_plans import (
    find_project_dir_for_session as find_project_dir_for_session,
)
from erk_shared.extraction.local_plans import (
    get_latest_plan_content,
)


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

    return get_latest_plan_content(session_id=session_id)


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
