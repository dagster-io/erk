"""Submit current branch as a pull request.

Uses Python operations with AI executor for commit message generation.
"""

import uuid
from pathlib import Path

import click
from erk_shared.integrations.ai.real import RealClaudeCLIExecutor
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.operations.submit_pr import execute_submit_pr
from erk_shared.integrations.gt.types import SubmitPRError, SubmitPRResult

from erk.cli.commands.pr.adapters import ContextGtKit
from erk.core.context import ErkContext


def _generate_session_id() -> str:
    """Generate a unique session ID for scratch file isolation."""
    return uuid.uuid4().hex


@click.command("submit")
@click.option("-f", "--force", is_flag=True, help="Force push even if remote has diverged")
@click.pass_obj
def pr_submit(ctx: ErkContext, force: bool) -> None:
    """Submit PR with AI-generated commit message.

    Analyzes your changes, generates a commit message via AI, and
    creates a pull request using Graphite.

    Examples:

    \b
      # Submit PR
      erk pr submit

      # Force push if remote has diverged
      erk pr submit --force
    """
    click.echo(click.style("🚀 Submitting PR...", bold=True))

    # Build GtKit from context components + real AI executor
    ops = ContextGtKit.from_context(ctx, ai=RealClaudeCLIExecutor())
    cwd = Path.cwd()
    session_id = _generate_session_id()

    # Execute the unified submit workflow
    for event in execute_submit_pr(ops, cwd, session_id, force=force):
        if isinstance(event, ProgressEvent):
            # Display progress with appropriate styling
            style_map = {
                "success": "green",
                "warning": "yellow",
                "error": "red",
                "info": None,
            }
            fg_color = style_map.get(event.style)
            prefix = "   " if event.style != "error" else "❌ "
            click.echo(click.style(f"{prefix}{event.message}", fg=fg_color))
        elif isinstance(event, CompletionEvent):
            result = event.result
            if isinstance(result, SubmitPRResult):
                # Success - display PR URLs
                click.echo("")
                styled_url = click.style(result.pr_url, fg="cyan", underline=True)
                clickable_url = f"\033]8;;{result.pr_url}\033\\{styled_url}\033]8;;\033\\"
                click.echo(f"✅ {clickable_url}")
                if result.graphite_url:
                    styled_graphite = click.style(result.graphite_url, fg="blue", underline=True)
                    clickable_graphite = (
                        f"\033]8;;{result.graphite_url}\033\\{styled_graphite}\033]8;;\033\\"
                    )
                    click.echo(f"   Graphite: {clickable_graphite}")
            elif isinstance(result, SubmitPRError):
                # Error - display error details and exit
                click.echo("")
                click.echo(click.style(f"❌ {result.error_type}: {result.message}", fg="red"))
                if result.details:
                    for key, value in result.details.items():
                        click.echo(click.style(f"   {key}: {value}", fg="red", dim=True))
                raise click.ClickException(result.message)
