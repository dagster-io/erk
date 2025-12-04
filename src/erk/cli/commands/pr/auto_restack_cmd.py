"""Automate Graphite restacking with intelligent conflict resolution.

Delegates to the /erk:auto-restack slash command via Claude CLI.
"""

from pathlib import Path

import click

from erk.cli.output import stream_auto_restack
from erk.core.context import ErkContext


@click.command("auto-restack")
@click.pass_obj
def pr_auto_restack(ctx: ErkContext) -> None:
    """Restack with AI-powered conflict resolution.

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

    result = stream_auto_restack(executor, Path.cwd())

    if result.requires_interactive:
        raise click.ClickException("Semantic conflict requires interactive resolution")
    if not result.success:
        raise click.ClickException(result.error_message or "Auto-restack failed")

    click.echo("\n✅ Restack complete!")
