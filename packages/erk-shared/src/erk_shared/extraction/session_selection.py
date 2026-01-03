"""Session selection logic for extraction workflow.

This module provides the auto-selection algorithm for choosing
which sessions to include in an extraction plan.
"""

from erk_shared.extraction.claude_installation import Session
from erk_shared.extraction.types import BranchContext

# Default threshold for considering a session "substantial"
DEFAULT_MIN_SUBSTANTIAL_SIZE = 1024


def auto_select_sessions(
    sessions: list[Session],
    branch_context: BranchContext,
    current_session_id: str | None,
    min_substantial_size: int = DEFAULT_MIN_SUBSTANTIAL_SIZE,
) -> list[Session]:
    """Auto-select sessions based on branch context.

    Rules:
    - If on trunk: use current session only
    - If current session is trivial (<min_size) AND substantial sessions exist:
      auto-select substantial sessions
    - If current session is substantial: use it

    Args:
        sessions: List of available sessions (already filtered by min_size)
        branch_context: Git branch context with trunk status
        current_session_id: The current active session ID
        min_substantial_size: Minimum size in bytes to consider a session substantial

    Returns:
        List of sessions to include in extraction
    """
    # Find current session by ID (not by is_current flag, which depends on env var)
    current_session = next((s for s in sessions if s.session_id == current_session_id), None)

    # If on trunk, only use current session (if found)
    if branch_context.is_on_trunk:
        return [current_session] if current_session else []

    # If no current session found, return all substantial sessions
    if current_session is None:
        return [s for s in sessions if s.size_bytes >= min_substantial_size]

    # Check if current session is substantial
    current_is_substantial = current_session.size_bytes >= min_substantial_size

    if current_is_substantial:
        # Use current session only
        return [current_session]

    # Current session is trivial - check for substantial sessions
    substantial_sessions = [s for s in sessions if s.size_bytes >= min_substantial_size]

    if substantial_sessions:
        # Auto-select substantial sessions (excluding trivial current)
        return substantial_sessions

    # No substantial sessions exist - return current (even if trivial)
    return [current_session]
