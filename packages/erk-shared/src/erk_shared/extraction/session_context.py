"""Session context collection for embedding in GitHub issues.

This module provides a shared helper for collecting and preprocessing
session context that can be embedded in GitHub issues. Used by both
plan-save-to-issue and raw extraction workflows.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.extraction.claude_installation import ClaudeInstallation
from erk_shared.extraction.session_discovery import get_branch_context
from erk_shared.extraction.session_preprocessing import preprocess_session_content
from erk_shared.extraction.session_selection import auto_select_sessions
from erk_shared.extraction.types import BranchContext
from erk_shared.git.abc import Git


@dataclass(frozen=True)
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
    claude_installation: ClaudeInstallation,
    current_session_id: str | None,
    min_size: int,
    limit: int,
) -> SessionContextResult | None:
    """Discover, select, and preprocess sessions into combined XML.

    This is the shared orchestrator for session context collection.
    It handles:
    1. Checking if project exists via ClaudeInstallation
    2. Getting branch context
    3. Discovering available sessions
    4. Auto-selecting based on branch context
    5. Preprocessing selected sessions to XML
    6. Combining multiple sessions into single XML

    Args:
        git: Git interface for branch operations
        cwd: Current working directory (for project directory lookup)
        claude_installation: ClaudeInstallation for session operations
        current_session_id: Current session ID (required for session context)
        min_size: Minimum session size in bytes for selection
        limit: Maximum number of sessions to discover

    Returns:
        SessionContextResult with combined XML and metadata,
        or None if:
        - No project exists
        - No current session ID provided
        - No sessions discovered
        - All sessions empty after preprocessing
    """
    if current_session_id is None:
        return None

    # Check if project exists
    if not claude_installation.has_project(cwd):
        return None

    # Get branch context
    branch_context = get_branch_context(git, cwd)

    # Discover sessions
    sessions = claude_installation.find_sessions(
        cwd,
        current_session_id=current_session_id,
        min_size=min_size,
        limit=limit,
        include_agents=False,
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
        session_content = claude_installation.read_session(
            cwd,
            session.session_id,
            include_agents=True,
        )
        if session_content is None:
            continue

        xml_content = preprocess_session_content(
            main_content=session_content.main_content,
            agent_logs=session_content.agent_logs,
            session_id=session.session_id,
        )
        # Skip semantically empty sessions (just <session>\n</session> wrapper)
        is_empty_xml = xml_content.strip() in ("", "<session>\n</session>")
        if xml_content and not is_empty_xml:
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
