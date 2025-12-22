"""Show details for a specific Claude Code session."""

import json
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import click
from rich.console import Console

from erk.cli.commands.cc.session.list_cmd import (
    extract_summary,
    format_display_time,
    format_size,
)
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext
from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore


def _parse_timestamp(value: str | float | int | None) -> float | None:
    """Parse a timestamp value to Unix float.

    Handles:
    - None -> None
    - float/int -> returned as-is
    - ISO 8601 string (e.g., "2024-12-22T13:20:00.000Z") -> Unix timestamp

    Args:
        value: Timestamp as float, int, ISO string, or None

    Returns:
        Unix timestamp as float, or None if value is None

    Raises:
        ValueError: If string timestamp is not valid ISO 8601 format
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Handle "Z" suffix (UTC)
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        return dt.timestamp()
    msg = f"Unexpected timestamp type: {type(value)}"
    raise TypeError(msg)


class AgentInvocation(NamedTuple):
    """Information about an agent session extracted from Task invocation."""

    agent_type: str
    prompt: str
    duration_secs: float | None


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


def extract_agent_info(parent_content: str) -> dict[str, AgentInvocation]:
    """Extract agent info from Task tool invocations and their results.

    Uses explicit metadata linking:
    1. Task tool_use entries contain: tool_use.id -> (subagent_type, description)
    2. tool_result entries contain: tool_use_id + toolUseResult.agentId

    Duration is calculated from entry-level timestamps:
    - tool_use timestamp (when Task was invoked)
    - tool_result timestamp (when Task completed)

    This provides deterministic matching without timestamp correlation.

    Args:
        parent_content: JSONL content of parent session

    Returns:
        Dict mapping "agent-<id>" session IDs to AgentInvocation
    """
    # Step 1: Collect Task tool_use entries: tool_use_id -> (type, prompt, timestamp)
    task_info: dict[str, tuple[str, str, float | None]] = {}

    # Step 2: Collect tool_result entries: tool_use_id -> (agentId, timestamp)
    tool_to_agent: dict[str, tuple[str, float | None]] = {}

    for line in parent_content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue

        entry = json.loads(stripped)

        entry_type = entry.get("type")
        message = entry.get("message", {})
        # Timestamp is at root level of entry (may be Unix float or ISO string)
        timestamp = _parse_timestamp(entry.get("timestamp"))

        if entry_type == "assistant":
            # Look for Task tool_use blocks
            for block in message.get("content", []):
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") != "Task":
                    continue

                tool_use_id = block.get("id")
                tool_input = block.get("input", {})
                subagent_type = tool_input.get("subagent_type", "")
                prompt = tool_input.get("prompt", "")

                if tool_use_id:
                    task_info[tool_use_id] = (subagent_type, prompt, timestamp)

        elif entry_type == "user":
            # Look for tool_result with toolUseResult.agentId
            tool_use_result = entry.get("toolUseResult")
            if not isinstance(tool_use_result, dict):
                continue
            agent_id = tool_use_result.get("agentId")

            if agent_id:
                # Find the tool_use_id from message content
                for block in message.get("content", []):
                    if block.get("type") != "tool_result":
                        continue
                    tool_use_id = block.get("tool_use_id")
                    if tool_use_id:
                        tool_to_agent[tool_use_id] = (agent_id, timestamp)

    # Step 3: Build final mapping: agent-<id> -> AgentInvocation
    agent_infos: dict[str, AgentInvocation] = {}
    for tool_use_id, (agent_id, result_timestamp) in tool_to_agent.items():
        info = task_info.get(tool_use_id)
        if info:
            subagent_type, prompt, use_timestamp = info
            # Calculate duration if both timestamps available
            duration_secs: float | None = None
            if use_timestamp is not None and result_timestamp is not None:
                duration_secs = result_timestamp - use_timestamp
            session_id = f"agent-{agent_id}"
            agent_infos[session_id] = AgentInvocation(
                agent_type=subagent_type,
                prompt=prompt,
                duration_secs=duration_secs,
            )

    return agent_infos


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
    Ensure.invariant(
        session_store.has_project(cwd),
        f"No Claude Code sessions found for: {cwd}",
    )

    # If no session_id provided, use the most recent session
    inferred = False
    if session_id is None:
        sessions = session_store.find_sessions(cwd, include_agents=False, limit=1)
        Ensure.invariant(len(sessions) > 0, "No sessions found.")
        session_id = sessions[0].session_id
        inferred = True

    # Get the session
    session = Ensure.session(session_store.get_session(cwd, session_id))

    # Check if this is an agent session - provide helpful error
    parent_id = session.parent_session_id
    Ensure.invariant(
        parent_id is None,
        f"Cannot show agent session directly. Use parent session instead: {parent_id}",
    )

    # Get the session path
    session_path = session_store.get_session_path(cwd, session_id)

    # Read session content for summary and agent info extraction
    content = session_store.read_session(cwd, session_id, include_agents=False)
    summary = ""
    agent_infos: dict[str, AgentInvocation] = {}
    if content is not None:
        summary = extract_summary(content.main_content, max_length=100)
        agent_infos = extract_agent_info(content.main_content)

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
    all_sessions = session_store.find_sessions(cwd, include_agents=True, limit=1000)

    # Filter to only agent sessions with this parent
    child_agents = [s for s in all_sessions if s.parent_session_id == session_id]

    if child_agents:
        console.print()
        console.print("[bold]Agent Sessions:[/bold]")

        for agent in child_agents:
            info = agent_infos.get(agent.session_id)
            agent_path = session_store.get_session_path(cwd, agent.session_id)

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
        ctx.session_store,
        ctx.cwd,
        session_id,
    )
