"""Show details of a Claude Code session including agent tasks."""

import json
from pathlib import Path
from typing import NamedTuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from erk.cli.commands.cc.session.list_cmd import (
    format_display_time,
    format_size,
)
from erk.core.context import ErkContext
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore


class AgentInfo(NamedTuple):
    """Information about an agent task invocation."""

    agent_type: str
    prompt: str
    duration_secs: float | None


def format_duration(seconds: float) -> str:
    """Format duration in seconds as human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable duration string like "42s", "2m 15s", or "1h 30m"
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"


def extract_agent_info(content: str) -> list[AgentInfo]:
    """Extract agent task information from session content.

    Parses the session JSONL to find Task tool_use entries and their
    corresponding tool_result entries. Computes duration from timestamps.

    Args:
        content: Raw JSONL session content

    Returns:
        List of AgentInfo for each Task tool invocation found
    """
    agents: list[AgentInfo] = []
    tool_use_timestamps: dict[str, float] = {}
    tool_use_info: dict[str, tuple[str, str]] = {}  # id -> (agent_type, prompt)

    for line in content.split("\n"):
        if not line.strip():
            continue
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue

        entry = json.loads(stripped)
        entry_type = entry.get("type")
        message = entry.get("message", {})
        timestamp = entry.get("timestamp")

        if entry_type == "assistant":
            content_blocks = message.get("content", [])
            if isinstance(content_blocks, list):
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        if block.get("name") == "Task":
                            tool_use_id = block.get("id", "")
                            tool_input = block.get("input", {})
                            agent_type = tool_input.get("subagent_type", "unknown")
                            prompt = tool_input.get("prompt", "")
                            # Truncate prompt for display
                            if len(prompt) > 50:
                                prompt = prompt[:47] + "..."
                            tool_use_info[tool_use_id] = (agent_type, prompt)
                            if timestamp is not None:
                                tool_use_timestamps[tool_use_id] = timestamp

        elif entry_type == "tool_result":
            tool_use_id = message.get("tool_use_id", "")
            if tool_use_id in tool_use_info:
                agent_type, prompt = tool_use_info[tool_use_id]
                duration_secs: float | None = None
                if tool_use_id in tool_use_timestamps and timestamp is not None:
                    duration_secs = timestamp - tool_use_timestamps[tool_use_id]
                agents.append(AgentInfo(agent_type, prompt, duration_secs))

    return agents


def _show_session_impl(
    session_store: ClaudeCodeSessionStore,
    cwd: Path,
    session_id: str,
) -> None:
    """Implementation of session show logic.

    Args:
        session_store: Session store to query
        cwd: Current working directory (project identifier)
        session_id: ID of the session to show
    """
    # Check if project exists
    if not session_store.has_project(cwd):
        click.echo(f"No Claude Code sessions found for: {cwd}", err=True)
        raise SystemExit(1)

    # Read session content
    session_content = session_store.read_session(cwd, session_id, include_agents=False)
    if session_content is None:
        click.echo(f"Session not found: {session_id}", err=True)
        raise SystemExit(1)

    # Get session metadata
    sessions = session_store.find_sessions(cwd, min_size=0, limit=1000, include_agents=False)
    session_meta = next((s for s in sessions if s.session_id == session_id), None)

    console = Console(stderr=True, force_terminal=True)

    # Show session header
    if session_meta is not None:
        header = f"Session: {session_id}"
        subtitle = f"{format_display_time(session_meta.modified_at)}  {format_size(session_meta.size_bytes)}"
        console.print(Panel(subtitle, title=header, expand=False))
    else:
        console.print(f"[bold]Session:[/bold] {session_id}")

    # Extract and display agent info
    agents = extract_agent_info(session_content.main_content)

    if agents:
        console.print()
        console.print("[bold]Agent Tasks:[/bold]")

        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("type", style="cyan", no_wrap=True)
        table.add_column("prompt", no_wrap=False)
        table.add_column("duration", no_wrap=True, justify="right")

        for agent in agents:
            duration_str = format_duration(agent.duration_secs) if agent.duration_secs is not None else "-"
            table.add_row(agent.agent_type, agent.prompt, duration_str)

        console.print(table)
    else:
        console.print()
        console.print("[dim]No agent tasks found in this session.[/dim]")


@click.command("show")
@click.argument("session_id")
@click.pass_obj
def show_session(ctx: ErkContext, session_id: str) -> None:
    """Show details of a Claude Code session.

    Displays session metadata and a list of agent tasks (Task tool invocations)
    with their types, prompts, and durations.
    """
    _show_session_impl(
        ctx.session_store,
        ctx.cwd,
        session_id,
    )
