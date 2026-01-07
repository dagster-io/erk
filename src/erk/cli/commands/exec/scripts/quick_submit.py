"""Quick commit all changes and submit with Graphite or git push."""

import json
from dataclasses import asdict

import click

from erk_shared.context.helpers import require_cwd
from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.operations.quick_submit import execute_quick_submit
from erk_shared.gateway.gt.types import QuickSubmitError


@click.command("quick-submit")
@click.pass_context
def quick_submit(ctx: click.Context) -> None:
    """Quick commit all changes and submit.

    Stages all changes, commits with "update" message if there are changes,
    then submits via Graphite (gt submit) or git push depending on config.
    This is a fast iteration shortcut.

    For proper commit messages, use the pr-submit command instead.
    """
    cwd = require_cwd(ctx)
    # ErkContext satisfies GtKit Protocol (git, github, graphite, time, branch_manager)
    result = render_events(execute_quick_submit(ctx.obj, cwd))

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    if isinstance(result, QuickSubmitError):
        raise SystemExit(1)
