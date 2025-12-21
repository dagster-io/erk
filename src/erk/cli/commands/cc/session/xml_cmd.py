"""Export Claude Code session as preprocessed XML."""

from pathlib import Path

import click

from erk.core.context import ErkContext
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore
from erk_shared.extraction.claude_code_session_store.abc import Session
from erk_shared.extraction.session_preprocessing import preprocess_session_content


class SessionIdResolutionError(Exception):
    """Raised when session ID cannot be uniquely resolved."""


def resolve_session_id(
    sessions: list[Session],
    session_id: str,
) -> str:
    """Resolve a session ID (full GUID or 8-char prefix) to a full session ID.

    Args:
        sessions: List of available sessions
        session_id: Full GUID or 8-character prefix

    Returns:
        Full session ID

    Raises:
        SessionIdResolutionError: If no match or multiple matches found
    """
    # Check for exact match first
    for session in sessions:
        if session.session_id == session_id:
            return session.session_id

    # Try prefix matching
    matches = [s for s in sessions if s.session_id.startswith(session_id)]

    if len(matches) == 0:
        raise SessionIdResolutionError(f"No session found matching: {session_id}")

    if len(matches) > 1:
        matching_ids = [s.session_id[:8] for s in matches]
        raise SessionIdResolutionError(
            f"Multiple sessions match prefix '{session_id}': {', '.join(matching_ids)}"
        )

    return matches[0].session_id


def _session_xml_impl(
    session_store: ClaudeCodeSessionStore,
    cwd: Path,
    session_id: str,
) -> None:
    """Implementation of session XML export logic.

    Args:
        session_store: Session store to query
        cwd: Current working directory (project identifier)
        session_id: Session ID (full GUID or 8-char prefix)
    """
    # Check if project exists
    if not session_store.has_project(cwd):
        click.echo(f"No Claude Code sessions found for: {cwd}", err=True)
        raise SystemExit(1)

    # Get all sessions to resolve the ID
    sessions = session_store.find_sessions(cwd, limit=1000)

    if not sessions:
        click.echo("No sessions found.", err=True)
        raise SystemExit(1)

    # Resolve session ID
    try:
        full_session_id = resolve_session_id(sessions, session_id)
    except SessionIdResolutionError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e

    # Read session content with agent logs
    session_content = session_store.read_session(cwd, full_session_id, include_agents=True)

    if session_content is None:
        click.echo(f"Error: Could not read session: {full_session_id}", err=True)
        raise SystemExit(1)

    # Preprocess to XML
    xml_output = preprocess_session_content(
        session_content.main_content,
        session_content.agent_logs,
        session_id=full_session_id,
    )

    # Output to stdout
    click.echo(xml_output)


@click.command("xml")
@click.option(
    "--session-id",
    required=True,
    help="Session ID (full GUID or 8-char prefix)",
)
@click.pass_obj
def session_xml(ctx: ErkContext, session_id: str) -> None:
    """Export a session as preprocessed XML.

    Outputs the session in a compressed XML format suitable for further processing.
    The session ID can be a full GUID or an 8-character prefix.
    """
    _session_xml_impl(ctx.session_store, ctx.cwd, session_id)
