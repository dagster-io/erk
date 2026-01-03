"""Show details for a specific Claude Code session."""

from pathlib import Path

import click
from rich.console import Console

from erk.cli.commands.cc.session.list_cmd import (
    format_display_time,
    format_size,
)
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.extraction.claude_installation import ClaudeInstallation
from erk_shared.extraction.session_schema import (
    AgentInfo,
    extract_agent_info_from_jsonl,
    extract_first_user_message_text,
)


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "42s", "1m 30s", or "1h 15m"
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def _show_session_impl(
    claude_installation: ClaudeInstallation,
    cwd: Path,
    session_id: str | None,
) -> None:
    """Implementation of session show logic.

    Args:
        claude_installation: Claude installation to query
        cwd: Current working directory (project identifier)
        session_id: Session ID to show details for, or None to use most recent
    """
    console = Console(stderr=True, force_terminal=True)

    # Check if project exists
    Ensure.invariant(
        claude_installation.has_project(cwd),
        f"No Claude Code sessions found for: {cwd}",
    )

    # If no session_id provided, use the most recent session
    inferred = False
    if session_id is None:
        sessions = claude_installation.find_sessions(
            cwd,
            current_session_id=None,
            min_size=0,
            include_agents=False,
            limit=1,
        )
        Ensure.invariant(len(sessions) > 0, "No sessions found.")
        session_id = sessions[0].session_id
        inferred = True

    # Get the session
    session = Ensure.session(claude_installation.get_session(cwd, session_id))

    # Check if this is an agent session - provide helpful error
    parent_id = session.parent_session_id
    Ensure.invariant(
        parent_id is None,
        f"Cannot show agent session directly. Use parent session instead: {parent_id}",
    )

    # Get the session path
    session_path = claude_installation.get_session_path(cwd, session_id)

    # Read session content for summary and agent info extraction
    content = claude_installation.read_session(cwd, session_id, include_agents=False)
    summary = ""
    agent_infos: dict[str, AgentInfo] = {}
    if content is not None:
        summary = extract_first_user_message_text(content.main_content, max_length=100)
        agent_infos = extract_agent_info_from_jsonl(content.main_content)

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
    all_sessions = claude_installation.find_sessions(
        cwd,
        current_session_id=None,
        min_size=0,
        include_agents=True,
        limit=1000,
    )

    # Filter to only agent sessions with this parent
    child_agents = [s for s in all_sessions if s.parent_session_id == session_id]

    if child_agents:
        console.print()
        console.print("[bold]Agent Sessions:[/bold]")

        for agent in child_agents:
            info = agent_infos.get(agent.session_id)
            agent_path = claude_installation.get_session_path(cwd, agent.session_id)

            console.print()
            # Format: type("prompt") or just session_id if no info
            if info and info.agent_type:
                # Clean up prompt: collapse whitespace, truncate
                prompt_clean = " ".join(info.prompt.split())
                if len(prompt_clean) > 80:
                    prompt_preview = prompt_clean[:80] + "..."
                else:
                    prompt_preview = prompt_clean
                console.print(f'  [cyan]{info.agent_type}[/cyan]("{prompt_preview}")')
            else:
                console.print(f"  [cyan]{agent.session_id}[/cyan]")
            # Build metadata line: time, size, and optional duration
            metadata_parts = [
                format_display_time(agent.modified_at),
                format_size(agent.size_bytes),
            ]
            if info and info.duration_secs is not None:
                metadata_parts.append(format_duration(info.duration_secs))
            console.print(f"    {'  '.join(metadata_parts)}")
            if agent_path:
                console.print(f"    {agent_path}")
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
        ctx.claude_installation,
        ctx.cwd,
        session_id,
    )
