"""Prepare local branch for PR submission.

Delegates to the /gt:prepare-local slash command via Claude CLI.
"""

from pathlib import Path

import click

from erk.core.context import ErkContext


@click.command("prepare-local")
@click.pass_obj
def pr_prepare_local(ctx: ErkContext) -> None:
    """Squash commits with AI-generated message (no push).

    Squashes commits and generates a commit message.
    Uses PR body if available, otherwise AI-generates from diff.
    Does NOT push - run 'gt submit -f' after reviewing.

    Examples:

    \b
      # Prepare branch locally
      erk pr prepare-local

      # Then review and push
      git log -1
      gt submit -f
    """
    executor = ctx.claude_executor

    # Verify Claude is available
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

    click.echo(click.style("🔧 Preparing branch locally via Claude...", bold=True))
    click.echo(click.style("   (Claude may take a moment to start)", dim=True))
    click.echo("")

    worktree_path = Path.cwd()

    # Track results from streaming events
    error_message: str | None = None
    success = True
    last_spinner: str | None = None

    # Stream events and print content directly
    for event in executor.execute_command_streaming(
        command="/gt:prepare-local",
        worktree_path=worktree_path,
        dangerous=False,
    ):
        if event.event_type == "text":
            # Print text content directly (Claude's formatted output)
            click.echo(event.content)
        elif event.event_type == "tool":
            # Tool summaries with icon
            click.echo(click.style(f"   ⚙️  {event.content}", fg="cyan", dim=True))
        elif event.event_type == "spinner_update":
            # Deduplicate spinner updates
            if event.content != last_spinner:
                click.echo(click.style(f"   ⏳ {event.content}", dim=True))
                last_spinner = event.content
        elif event.event_type == "error":
            click.echo(click.style(f"   ❌ {event.content}", fg="red"))
            error_message = event.content
            success = False

    if not success:
        error_msg = error_message or "Branch preparation failed"
        raise click.ClickException(error_msg)
