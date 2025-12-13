"""Quick commit all changes and submit with Graphite CLI command."""

import json
from dataclasses import asdict
from pathlib import Path

import click

from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.quick_submit import execute_quick_submit
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.types import QuickSubmitError


@click.command("quick-submit")
def quick_submit() -> None:
    """Quick commit all changes and submit with Graphite.

    Stages all changes, commits with "update" message if there are changes,
    then runs gt submit. This is a fast iteration shortcut.

    For proper commit messages, use the pr-submit command instead.
    """
    cwd = Path.cwd()
    ops = RealGtKit(cwd)
    result = render_events(execute_quick_submit(ops, cwd))

    # Output JSON result
    click.echo(json.dumps(asdict(result), indent=2))

    if isinstance(result, QuickSubmitError):
        raise SystemExit(1)
