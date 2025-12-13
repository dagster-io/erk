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
