"""Restack continue CLI command.

Stage resolved files and continue restack, checking for more conflicts.
"""

import json
from dataclasses import asdict
from pathlib import Path

import click

from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.restack_continue import execute_restack_continue
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.types import RestackContinueError


@click.command(name="restack-continue")
@click.argument("resolved_files", nargs=-1, required=True)
def restack_continue(resolved_files: tuple[str, ...]) -> None:
    """Stage resolved files and continue restack.

    RESOLVED_FILES: Space-separated list of file paths that were resolved.
    """
    cwd = Path.cwd()
    ops = RealGtKit(cwd)
    result = render_events(execute_restack_continue(ops, cwd, list(resolved_files)))
    click.echo(json.dumps(asdict(result), indent=2))
    if isinstance(result, RestackContinueError):
        raise SystemExit(1)
