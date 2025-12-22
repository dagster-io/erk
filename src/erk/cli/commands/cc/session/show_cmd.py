"""Show details for a specific Claude Code session."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from erk.cli.commands.cc.session.list_cmd import (
    extract_summary,
    format_display_time,
    format_size,
)
from erk.core.context import ErkContext
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore


def _show_session_impl(
    session_store: ClaudeCodeSessionStore,
    cwd: Path,
    session_id: str | None,
) -> None:
    """Implementation of session show logic.

    Args:
        session_store: Session store to query
        cwd: Current working directory (project identifier)
        session_id: Session ID to show details for, or None to use most recent
    """
    console = Console(stderr=True, force_terminal=True)

    # Check if project exists
    if not session_store.has_project(cwd):
        click.echo(f"No Claude Code sessions found for: {cwd}", err=True)
        raise SystemExit(1)

    # If no session_id provided, use the most recent session
    inferred = False
    if session_id is None:
        sessions = session_store.find_sessions(cwd, include_agents=False, limit=1)
        if not sessions:
            click.echo("No sessions found.", err=True)
            raise SystemExit(1)
        session_id = sessions[0].session_id
        inferred = True

    # Get the session
    session = session_store.get_session(cwd, session_id)
    if session is None:
        click.echo(f"Session not found: {session_id}", err=True)
        raise SystemExit(1)

    # Check if this is an agent session - provide helpful error
    if session.parent_session_id is not None:
        parent_id = session.parent_session_id
        click.echo(
            f"Cannot show agent session directly. Use parent session instead: {parent_id}",
            err=True,
        )
        raise SystemExit(1)

    # Get the session path
    session_path = session_store.get_session_path(cwd, session_id)

    # Read session content for summary
    content = session_store.read_session(cwd, session_id, include_agents=False)
    summary = ""
    if content is not None:
        summary = extract_summary(content.main_content, max_length=100)

    # Print inferred message if applicable
    if inferred:
        msg = f"Using most recent session for this worktree: {session.session_id}"
        console.print(f"[dim]{msg}[/dim]")
        console.print()

    # Display metadata as key-value pairs
    console.print(f"[bold]ID:[/bold] {session.session_id}")
    console.print(f"[bold]Size:[/bold] {format_size(session.size_bytes)}")
    console.print(f"[bold]Modified:[/bold] {format_display_time(session.modified_at)}")
    if summary:
        console.print(f"[bold]Summary:[/bold] {summary}")
    if session_path is not None:
        console.print(f"[bold]Path:[/bold] {session_path}")

    # Find and display child agent sessions
    all_sessions = session_store.find_sessions(
        cwd, include_agents=True, limit=1000
    )

    # Filter to only agent sessions with this parent
    child_agents = [
        s for s in all_sessions if s.parent_session_id == session_id
    ]

    if child_agents:
        console.print()
        console.print("[bold]Agent Sessions:[/bold]")

        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("id", style="cyan", no_wrap=True)
        table.add_column("time", no_wrap=True)
        table.add_column("size", no_wrap=True, justify="right")
        table.add_column("summary", no_wrap=False)

        for agent in child_agents:
            # Read agent content for summary
            agent_content = session_store.read_session(
                cwd, agent.session_id, include_agents=False
            )
            agent_summary = ""
            if agent_content is not None:
                agent_summary = extract_summary(agent_content.main_content)

            table.add_row(
                agent.session_id,
                format_display_time(agent.modified_at),
                format_size(agent.size_bytes),
                agent_summary,
            )

        console.print(table)
    else:
        console.print()
        console.print("[dim]No agent sessions[/dim]")


@click.command("show")
@click.argument("session_id", required=False, default=None)
@click.pass_obj
def show_session(ctx: ErkContext, session_id: str | None) -> None:
    """Show details for a specific Claude Code session.

    Displays session metadata (ID, size, modified time, path, summary)
    and lists any child agent sessions.

    If SESSION_ID is not provided, shows the most recent session.
    """
    _show_session_impl(
        ctx.session_store,
        ctx.cwd,
        session_id,
    )
