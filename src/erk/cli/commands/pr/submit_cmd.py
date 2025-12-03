"""Submit current branch as a pull request.

Delegates to the /gt:pr-submit slash command via Claude CLI.
"""

from pathlib import Path

import click

from erk.core.context import ErkContext


@click.command("submit")
@click.pass_obj
def pr_submit(ctx: ErkContext) -> None:
    """Submit PR with AI-generated commit message.

    Analyzes your changes, generates a commit message via AI, and
    creates a pull request using Graphite.

    Examples:

    \b
      # Submit PR
      erk pr submit
    """
    executor = ctx.claude_executor

    # Verify Claude is available
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

    click.echo(click.style("🚀 Submitting PR via Claude...", bold=True))
    click.echo(click.style("   (Claude may take a moment to start)", dim=True))
    click.echo("")

    worktree_path = Path.cwd()

    # Track results from streaming events
    pr_url: str | None = None
    error_message: str | None = None
    success = True
    last_spinner: str | None = None

    # Stream events and print content directly
    for event in executor.execute_command_streaming(
        command="/gt:pr-submit",
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
        elif event.event_type == "pr_url":
            pr_url = event.content
        elif event.event_type == "error":
            click.echo(click.style(f"   ❌ {event.content}", fg="red"))
            error_message = event.content
            success = False

    # Final PR link with clickable URL
    if pr_url:
        styled_url = click.style(pr_url, fg="cyan", underline=True)
        clickable_url = f"\033]8;;{pr_url}\033\\{styled_url}\033]8;;\033\\"
        click.echo(f"\n✅ {clickable_url}")

    if not success:
        error_msg = error_message or "PR submission failed"
        raise click.ClickException(error_msg)
