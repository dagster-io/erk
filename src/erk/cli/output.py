"""Output utilities for CLI commands with clear intent.

For user_output, machine_output, format_duration - import from erk_shared.output.
This module provides format_implement_summary and stream_command_with_feedback.
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path

import click
from rich.panel import Panel
from rich.text import Text

from erk.core.claude_executor import (
    ClaudeExecutor,
    CommandResult,
    ErrorEvent,
    IssueNumberEvent,
    NoOutputEvent,
    NoTurnsEvent,
    PrNumberEvent,
    ProcessErrorEvent,
    PrTitleEvent,
    PrUrlEvent,
    SpinnerUpdateEvent,
    TextEvent,
    ToolEvent,
)
from erk_shared.output.output import format_duration


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
    model: str | None = None,
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
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        debug: Whether to show debug output for stream parsing

    Returns:
        CommandResult with success status, PR URL, duration, and messages
    """
    # Flush stderr to ensure previous user_output() messages are visible
    # before stdout starts printing. This prevents buffering issues where
    # stderr output appears after stdout in mixed output scenarios.
    sys.stderr.flush()

    # Print start marker (stderr so shell integration can capture stdout)
    click.echo(click.style(f"--- {command} ---", bold=True), err=True)

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
        command, worktree_path, dangerous, verbose=False, debug=debug, model=model
    )
    if debug:
        click.echo(click.style("[DEBUG] Starting event stream...", fg="yellow"), err=True)
    for event in event_stream:
        event_count += 1
        if debug:
            click.echo(
                click.style(f"[DEBUG] Event #{event_count}: {type(event).__name__}", fg="yellow"),
                err=True,
            )
        match event:
            case TextEvent(content=content):
                click.echo(content, err=True)
                filtered_messages.append(content)
            case ToolEvent(summary=summary):
                click.echo(click.style(f"  > {summary}", dim=True), err=True)
                filtered_messages.append(summary)
            case SpinnerUpdateEvent(status=status):
                # Deduplicate spinner updates - only print when status changes
                if status != last_spinner_update:
                    click.echo(click.style(f"  ... {status}", dim=True), err=True)
                    last_spinner_update = status
            case PrUrlEvent(url=url):
                pr_url = url
            case PrNumberEvent(number=num):
                pr_number = num  # Already int, no conversion needed
            case PrTitleEvent(title=title):
                pr_title = title
            case IssueNumberEvent(number=num):
                issue_number = num  # Already int, no conversion needed
            case ErrorEvent(message=msg):
                click.echo(click.style(f"  ! {msg}", fg="red"), err=True)
                error_message = msg
                success = False
            case NoOutputEvent(diagnostic=diag):
                click.echo(click.style(f"  ⚠️ {diag}", fg="yellow"), err=True)
                error_message = diag
                success = False
            case NoTurnsEvent(diagnostic=diag):
                click.echo(click.style(f"  ⚠️ {diag}", fg="yellow"), err=True)
                error_message = diag
                success = False
            case ProcessErrorEvent(message=msg):
                click.echo(click.style(f"  ❌ {msg}", fg="red"), err=True)
                error_message = msg
                success = False

    if debug:
        msg = f"[DEBUG] Event stream complete. Total events: {event_count}"
        click.echo(click.style(msg, fg="yellow"), err=True)

    duration = time.time() - start_time
    duration_str = format_duration(duration)

    # Print end marker (stderr so shell integration can capture stdout)
    if success:
        click.echo(click.style(f"--- Done ({duration_str}) ---", fg="green", bold=True), err=True)
    else:
        click.echo(click.style(f"--- Failed ({duration_str}) ---", fg="red", bold=True), err=True)

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


@dataclass(frozen=True)
class FixConflictsResult:
    """Result from fix-conflicts streaming execution."""

    success: bool
    error_message: str | None = None
    requires_interactive: bool = False


def stream_fix_conflicts(
    executor: ClaudeExecutor,
    worktree_path: Path,
) -> FixConflictsResult:
    """Stream fix-conflicts command via Claude executor with live feedback.

    Handles the /erk:fix-conflicts command execution with:
    - Live output streaming with visual feedback
    - Semantic conflict detection (AskUserQuestion)
    - Deduped spinner updates
    - Rich console output with start/end markers

    Args:
        executor: Claude CLI executor
        worktree_path: Path to run the conflict resolution in

    Returns:
        FixConflictsResult with success status and error details
    """
    error_message: str | None = None
    success = True
    has_work_events = False
    last_spinner: str | None = None
    start_time = time.time()

    # Print start marker with bold styling
    click.echo(click.style("--- /erk:fix-conflicts ---", bold=True))
    click.echo("")

    for event in executor.execute_command_streaming(
        command="/erk:fix-conflicts",
        worktree_path=worktree_path,
        dangerous=True,  # Conflict resolution modifies git state
    ):
        match event:
            case TextEvent(content=content):
                has_work_events = True
                click.echo(content)
            case ToolEvent(summary=summary):
                has_work_events = True
                # Check for user input prompts (semantic conflict requiring decision)
                if "AskUserQuestion" in summary:
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
                    click.echo("Run conflict resolution interactively:")
                    click.echo("")
                    click.echo(click.style("    claude /erk:fix-conflicts", fg="cyan"))
                    click.echo("")
                    return FixConflictsResult(
                        success=False,
                        requires_interactive=True,
                    )
                # Tool summaries with icon
                click.echo(click.style(f"   ⚙️  {summary}", fg="cyan", dim=True))
            case SpinnerUpdateEvent(status=status):
                if status != last_spinner:
                    click.echo(click.style(f"   ⏳ {status}", dim=True))
                    last_spinner = status
            case ErrorEvent(message=msg):
                click.echo(click.style(f"   ❌ {msg}", fg="red"))
                error_message = msg
                success = False
            case NoOutputEvent(diagnostic=diag):
                click.echo(click.style(f"   ⚠️  {diag}", fg="yellow"))
                error_message = diag
                success = False
            case NoTurnsEvent(diagnostic=diag):
                click.echo(click.style(f"   ⚠️  {diag}", fg="yellow"))
                error_message = diag
                success = False
            case ProcessErrorEvent(message=msg):
                click.echo(click.style(f"   ❌ {msg}", fg="red"))
                error_message = msg
                success = False
            case PrUrlEvent() | PrNumberEvent() | PrTitleEvent() | IssueNumberEvent():
                pass  # PR metadata not relevant for fix-conflicts

    # Check for no-work-events failure mode
    if success and not has_work_events:
        success = False
        error_message = (
            "Claude completed without producing any output - "
            "check hooks or run 'claude /erk:fix-conflicts' directly to debug"
        )
        click.echo(click.style(f"   ⚠️  {error_message}", fg="yellow"))

    # Calculate duration and print end marker
    duration = time.time() - start_time
    duration_str = format_duration(duration)

    click.echo("")
    if success:
        click.echo(click.style(f"--- Done ({duration_str}) ---", fg="green", bold=True))
    else:
        click.echo(click.style(f"--- Failed ({duration_str}) ---", fg="red", bold=True))

    return FixConflictsResult(success=success, error_message=error_message)
