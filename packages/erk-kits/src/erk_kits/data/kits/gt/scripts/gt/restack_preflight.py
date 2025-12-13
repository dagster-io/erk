"""Restack preflight CLI command.

Squash commits and attempt gt restack, detecting conflicts for manual resolution.
"""

import json
from dataclasses import asdict
from pathlib import Path

import click

from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.restack_preflight import execute_restack_preflight
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.types import RestackPreflightError


@click.command(name="restack-preflight")
def restack_preflight() -> None:
    """Squash and restack branch, detecting conflicts for manual resolution."""
    cwd = Path.cwd()
    ops = RealGtKit(cwd)
    result = render_events(execute_restack_preflight(ops, cwd))
    click.echo(json.dumps(asdict(result), indent=2))
    if isinstance(result, RestackPreflightError):
        raise SystemExit(1)
