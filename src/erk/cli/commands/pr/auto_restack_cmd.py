"""Automate Graphite restacking with intelligent conflict resolution.

Delegates to the /erk:auto-restack slash command via Claude CLI.
"""

from pathlib import Path

import click

from erk.core.context import ErkContext


@click.command("auto-restack")
@click.pass_obj
def pr_auto_restack(ctx: ErkContext) -> None:
    """Automate Graphite restacking with intelligent conflict resolution.

    Runs `gt restack` and automatically handles any merge conflicts that arise,
    looping until the restack completes successfully.

    Conflicts are classified as:
    - Semantic: Alerts user for manual decision
    - Mechanical: Auto-resolves when safe

    Examples:

    \b
      # Auto-restack with conflict resolution
      erk pr auto-restack
    """
    executor = ctx.claude_executor

    # Verify Claude is available
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

    click.echo(click.style("🔄 Auto-restacking via Claude...", bold=True))
    click.echo(click.style("   (Claude may take a moment to start)", dim=True))
    click.echo("")

    worktree_path = Path.cwd()

    # Track results from streaming events
    error_message: str | None = None
    success = True
    last_spinner: str | None = None

    # Stream events and print content directly
    for event in executor.execute_command_streaming(
        command="/erk:auto-restack",
        worktree_path=worktree_path,
        dangerous=True,  # Restack modifies git state
    ):
        if event.event_type == "text":
            # Print text content directly (Claude's formatted output)
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
                raise click.ClickException("Semantic conflict requires interactive resolution")
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

    if success:
        click.echo("\n✅ Restack complete!")

    if not success:
        error_msg = error_message or "Auto-restack failed"
        raise click.ClickException(error_msg)
