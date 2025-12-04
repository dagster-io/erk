"""Output utilities for CLI commands with clear intent.

For user_output, machine_output, format_duration - import from erk_shared.output.
This module provides format_implement_summary and stream_command_with_feedback.
"""

import time
from dataclasses import dataclass
from pathlib import Path

import click
from erk_shared.output.output import format_duration
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from erk.core.claude_executor import ClaudeExecutor, CommandResult


def format_implement_summary(results: list[CommandResult], total_duration: float) -> Panel:
    """Format final summary box with status, PR link, timing, errors.

    Args:
        results: List of CommandResult from executed commands
        total_duration: Total execution time in seconds

    Returns:
        Rich Panel with formatted summary

    Example:
        >>> results = [CommandResult(success=True, pr_url="https://...", ...)]
        >>> panel = format_implement_summary(results, 123.45)
        >>> console.print(panel)
    """
    # Determine overall success
    overall_success = all(r.success for r in results)

    # Build summary lines
    lines: list[Text] = []

    # Status line
    if overall_success:
        lines.append(Text("✅ Status: Success", style="green"))
    else:
        lines.append(Text("❌ Status: Failed", style="red"))

    # Duration
    duration_str = format_duration(total_duration)
    lines.append(Text(f"⏱  Duration: {duration_str}"))

    # PR and issue metadata (if any)
    pr_url: str | None = None
    pr_number: int | None = None
    pr_title: str | None = None
    issue_number: int | None = None
    for result in results:
        if result.pr_url:
            pr_url = result.pr_url
            pr_number = result.pr_number
            pr_title = result.pr_title
            issue_number = result.issue_number
            break

    if pr_url:
        # Add blank line for spacing
        lines.append(Text(""))

        # Show PR number with URL
        if pr_number:
            lines.append(Text(f"🔗 PR: #{pr_number}", style="blue bold"))
        else:
            lines.append(Text("🔗 PR: Created", style="blue bold"))

        # Show PR title
        if pr_title:
            lines.append(Text(f"   {pr_title}", style="cyan"))

        # Show PR URL
        lines.append(Text(f"   {pr_url}", style="dim"))

        # Show linked issue (if any)
        if issue_number:
            lines.append(Text(""))
            lines.append(
                Text(f"📋 Linked Issue: #{issue_number} (will auto-close on merge)", style="yellow")
            )

    # Error details (if failed)
    if not overall_success:
        for i, result in enumerate(results):
            if not result.success:
                if result.error_message:
                    lines.append(Text(""))  # Blank line
                    lines.append(Text(f"Error in command {i + 1}:", style="red bold"))
                    lines.append(Text(result.error_message, style="red"))

    # Combine lines
    content = Text("\n").join(lines)

    # Create panel
    title = "Implementation Complete" if overall_success else "Implementation Failed"
    return Panel(
        content, title=title, border_style="green" if overall_success else "red", padding=(1, 2)
    )


def stream_command_with_feedback(
    executor: ClaudeExecutor,
    command: str,
    worktree_path: Path,
    dangerous: bool,
    console: Console | None = None,
    debug: bool = False,
) -> CommandResult:
    """Stream Claude command execution with live print-based feedback.

    This function replaces spinner-based output with print-based feedback
    that works correctly (Rich's console.status() suppresses console.print()).

    Visual output format:
    - Start: `--- /command ---` (bold)
    - Text events: content as-is (normal)
    - Tool events: `  > tool summary` (dim)
    - Spinner updates: `  ... status` (dim, deduplicated)
    - Error events: `  ! error message` (red)
    - End (success): `--- Done (1m 23s) ---` (green)
    - End (failure): `--- Failed (1m 23s) ---` (red)

    Args:
        executor: Claude CLI executor for command execution
        command: The slash command to execute (e.g., "/gt:pr-submit")
        worktree_path: Path to worktree directory to run command in
        dangerous: Whether to skip permission prompts
        console: Rich Console for output (if None, creates one with force_terminal=True)
        debug: Whether to show debug output for stream parsing

    Returns:
        CommandResult with success status, PR URL, duration, and messages
    """
    # Create console with force_terminal to ensure immediate output
    if console is None:
        console = Console(force_terminal=True)

    # Print start marker
    console.print(f"--- {command} ---", style="bold")

    start_time = time.time()
    filtered_messages: list[str] = []
    pr_url: str | None = None
    pr_number: int | None = None
    pr_title: str | None = None
    issue_number: int | None = None
    error_message: str | None = None
    success = True
    last_spinner_update: str | None = None
    event_count = 0

    # Stream events in real-time
    event_stream = executor.execute_command_streaming(
        command, worktree_path, dangerous, verbose=False, debug=debug
    )
    if debug:
        console.print("[DEBUG] Starting event stream...", style="yellow")
    for event in event_stream:
        event_count += 1
        if debug:
            content_preview = event.content[:80] if len(event.content) > 80 else event.content
            console.print(
                f"[DEBUG] Event #{event_count}: type={event.event_type!r}, "
                f"content={content_preview!r}",
                style="yellow",
            )
        if event.event_type == "text":
            console.print(event.content)
            filtered_messages.append(event.content)
        elif event.event_type == "tool":
            console.print(f"  > {event.content}", style="dim")
            filtered_messages.append(event.content)
        elif event.event_type == "spinner_update":
            # Deduplicate spinner updates - only print when status changes
            if event.content != last_spinner_update:
                console.print(f"  ... {event.content}", style="dim")
                last_spinner_update = event.content
        elif event.event_type == "pr_url":
            pr_url = event.content
        elif event.event_type == "pr_number":
            # Convert string back to int - safe because we control the source
            if event.content.isdigit():
                pr_number = int(event.content)
        elif event.event_type == "pr_title":
            pr_title = event.content
        elif event.event_type == "issue_number":
            # Convert string back to int - safe because we control the source
            if event.content.isdigit():
                issue_number = int(event.content)
        elif event.event_type == "error":
            console.print(f"  ! {event.content}", style="red")
            error_message = event.content
            success = False

    if debug:
        console.print(f"[DEBUG] Event stream complete. Total events: {event_count}", style="yellow")

    duration = time.time() - start_time
    duration_str = format_duration(duration)

    # Print end marker
    if success:
        console.print(f"--- Done ({duration_str}) ---", style="green")
    else:
        console.print(f"--- Failed ({duration_str}) ---", style="red")

    return CommandResult(
        success=success,
        pr_url=pr_url,
        pr_number=pr_number,
        pr_title=pr_title,
        issue_number=issue_number,
        duration_seconds=duration,
        error_message=error_message,
        filtered_messages=filtered_messages,
    )


@dataclass
class AutoRestackResult:
    """Result from auto-restack streaming execution."""

    success: bool
    error_message: str | None = None
    requires_interactive: bool = False


def stream_auto_restack(
    executor: ClaudeExecutor,
    worktree_path: Path,
) -> AutoRestackResult:
    """Stream auto-restack command via Claude executor with live feedback.

    Handles the /erk:auto-restack command execution with:
    - Live output streaming
    - Semantic conflict detection (AskUserQuestion)
    - Deduped spinner updates

    Args:
        executor: Claude CLI executor
        worktree_path: Path to run the restack in

    Returns:
        AutoRestackResult with success status and error details
    """
    error_message: str | None = None
    success = True
    last_spinner: str | None = None

    for event in executor.execute_command_streaming(
        command="/erk:auto-restack",
        worktree_path=worktree_path,
        dangerous=True,  # Restack modifies git state
    ):
        if event.event_type == "text":
            click.echo(event.content)
        elif event.event_type == "tool":
            # Check for user input prompts (semantic conflict requiring decision)
            if "AskUserQuestion" in event.content:
                click.echo("")
                click.echo(
                    click.style(
                        "⚠️  Semantic conflict detected - requires interactive resolution",
                        fg="yellow",
                        bold=True,
                    )
                )
                click.echo("")
                click.echo("Claude needs your input to resolve this conflict.")
                click.echo("Please run the restack manually in an interactive environment:")
                click.echo("")
                click.echo(click.style("    claude /erk:auto-restack", fg="cyan"))
                click.echo("")
                return AutoRestackResult(
                    success=False,
                    requires_interactive=True,
                )
            # Tool summaries with icon
            click.echo(click.style(f"   ⚙️  {event.content}", fg="cyan", dim=True))
        elif event.event_type == "spinner_update":
            if event.content != last_spinner:
                click.echo(click.style(f"   ⏳ {event.content}", dim=True))
                last_spinner = event.content
        elif event.event_type == "error":
            click.echo(click.style(f"   ❌ {event.content}", fg="red"))
            error_message = event.content
            success = False

    return AutoRestackResult(success=success, error_message=error_message)
