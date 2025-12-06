"""Session context collection for embedding in GitHub issues.

This module provides a shared helper for collecting and preprocessing
session context that can be embedded in GitHub issues. Used by both
plan-save-to-issue and raw extraction workflows.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.extraction.session_discovery import (
    discover_sessions,
    find_project_dir,
    get_branch_context,
    get_current_session_id,
)
from erk_shared.extraction.session_preprocessing import preprocess_session
from erk_shared.extraction.session_selection import auto_select_sessions
from erk_shared.extraction.types import BranchContext
from erk_shared.git.abc import Git


@dataclass
class SessionContextResult:
    """Result of session context collection.

    Attributes:
        combined_xml: Preprocessed session content as XML string
        session_ids: List of session IDs that were processed
        branch_context: Git branch context at time of collection
    """

    combined_xml: str
    session_ids: list[str]
    branch_context: BranchContext


def collect_session_context(
    git: Git,
    cwd: Path,
    current_session_id: str | None = None,
    min_size: int = 1024,
    limit: int = 20,
) -> SessionContextResult | None:
    """Discover, select, and preprocess sessions into combined XML.

    This is the shared orchestrator for session context collection.
    It handles:
    1. Finding the project directory
    2. Getting branch context
    3. Discovering available sessions
    4. Auto-selecting based on branch context
    5. Preprocessing selected sessions to XML
    6. Combining multiple sessions into single XML

    Args:
        git: Git interface for branch operations
        cwd: Current working directory (for project directory lookup)
        current_session_id: Current session ID (None to auto-detect from env)
        min_size: Minimum session size in bytes for selection
        limit: Maximum number of sessions to discover

    Returns:
        SessionContextResult with combined XML and metadata,
        or None if:
        - No project directory found
        - No current session ID available
        - No sessions discovered
        - All sessions empty after preprocessing
    """
    # Get current session ID if not provided
    if current_session_id is None:
        current_session_id = get_current_session_id()

    if current_session_id is None:
        return None

    # Find project directory
    project_dir = find_project_dir(cwd)
    if project_dir is None:
        return None

    # Get branch context
    branch_context = get_branch_context(git, cwd)

    # Discover sessions
    sessions = discover_sessions(
        project_dir=project_dir,
        current_session_id=current_session_id,
        min_size=min_size,
        limit=limit,
    )

    if not sessions:
        return None

    # Auto-select sessions based on branch context
    selected_sessions = auto_select_sessions(
        sessions=sessions,
        branch_context=branch_context,
        current_session_id=current_session_id,
        min_substantial_size=min_size,
    )

    if not selected_sessions:
        return None

    # Preprocess sessions to XML
    session_xmls: list[tuple[str, str]] = []
    for session in selected_sessions:
        xml_content = preprocess_session(
            session_path=session.path,
            session_id=session.session_id,
            include_agents=True,
        )
        if xml_content:  # Skip empty sessions
            session_xmls.append((session.session_id, xml_content))

    if not session_xmls:
        return None

    # Combine session XMLs
    if len(session_xmls) == 1:
        combined_xml = session_xmls[0][1]
    else:
        # Multiple sessions - concatenate with headers
        xml_parts = []
        for session_id, xml in session_xmls:
            xml_parts.append(f"<!-- Session: {session_id} -->\n{xml}")
        combined_xml = "\n\n".join(xml_parts)

    session_ids = [s for s, _ in session_xmls]

    return SessionContextResult(
        combined_xml=combined_xml,
        session_ids=session_ids,
        branch_context=branch_context,
    )
