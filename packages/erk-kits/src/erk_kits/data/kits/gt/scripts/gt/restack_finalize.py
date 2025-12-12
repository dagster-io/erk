"""Restack finalize CLI command.

Verify restack completed cleanly (no rebase in progress, clean working tree).
"""

import json
from dataclasses import asdict
from pathlib import Path

import click

from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.restack_finalize import execute_restack_finalize
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.types import RestackFinalizeError


@click.command(name="restack-finalize")
def restack_finalize() -> None:
    """Verify restack completed cleanly."""
    ops = RealGtKit()
    cwd = Path.cwd()
    result = render_events(execute_restack_finalize(ops, cwd))
    click.echo(json.dumps(asdict(result), indent=2))
    if isinstance(result, RestackFinalizeError):
        raise SystemExit(1)
