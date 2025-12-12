"""Automate Graphite restacking with intelligent conflict resolution.

Fast path: If restack succeeds without conflicts, completes without Claude.
Slow path: If conflicts detected, delegates to Claude for intelligent resolution.
"""

import click

from erk.cli.output import stream_auto_restack
from erk.core.context import ErkContext
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.operations.restack_finalize import execute_restack_finalize
from erk_shared.integrations.gt.operations.restack_preflight import execute_restack_preflight
from erk_shared.integrations.gt.types import (
    RestackFinalizeError,
    RestackPreflightError,
    RestackPreflightSuccess,
)


@click.command("auto-restack")
@click.option(
    "--dangerous",
    is_flag=True,
    required=True,
    help="Acknowledge that this command invokes Claude with --dangerously-skip-permissions.",
)
@click.pass_obj
def pr_auto_restack(ctx: ErkContext, *, dangerous: bool) -> None:
    """Restack with AI-powered conflict resolution.

    Runs `gt restack` and automatically handles any merge conflicts that arise,
    looping until the restack completes successfully.

    Conflicts are classified as:
    - Semantic: Alerts user for manual decision
    - Mechanical: Auto-resolves when safe

    Examples:

    \b
      # Auto-restack with conflict resolution
      erk pr auto-restack --dangerous
    """
    # dangerous flag is required to indicate acknowledgment
    _ = dangerous
    cwd = ctx.cwd

    # Phase 1: Try fast path (preflight: squash + attempt restack)
    preflight_result: RestackPreflightSuccess | RestackPreflightError | None = None
    for event in execute_restack_preflight(ctx, cwd):
        match event:
            case ProgressEvent(message=msg):
                click.echo(click.style(f"  {msg}", dim=True), err=True)
            case CompletionEvent(result=result):
                preflight_result = result

    # Handle preflight errors
    if isinstance(preflight_result, RestackPreflightError):
        raise click.ClickException(preflight_result.message)

    # Type guard: at this point preflight_result must be RestackPreflightSuccess
    if preflight_result is None:
        raise click.ClickException("Preflight operation did not complete")

    # Fast path success: No conflicts
    if not preflight_result.has_conflicts:
        # Verify completion
        for event in execute_restack_finalize(ctx, cwd):
            match event:
                case CompletionEvent(result=result):
                    if isinstance(result, RestackFinalizeError):
                        raise click.ClickException(result.message)

        click.echo(click.style("Restack complete!", fg="green", bold=True))
        return

    # Slow path: Conflicts detected, invoke Claude
    click.echo(
        click.style(
            f"Conflicts detected in {len(preflight_result.conflicts)} file(s). "
            "Falling back to Claude...",
            fg="yellow",
        )
    )

    executor = ctx.claude_executor
    if not executor.is_claude_available():
        raise click.ClickException(
            "Conflicts require Claude for resolution.\n\nInstall from: https://claude.com/download"
        )

    result = stream_auto_restack(executor, cwd)

    if result.requires_interactive:
        raise click.ClickException("Semantic conflict requires interactive resolution")
    if not result.success:
        raise click.ClickException(result.error_message or "Auto-restack failed")

    click.echo("\n✅ Restack complete!")
