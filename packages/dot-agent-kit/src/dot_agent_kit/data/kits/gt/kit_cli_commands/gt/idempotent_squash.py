"""Idempotent squash CLI command.

Squash commits on current branch (idempotent - skips if already single commit).
"""

import json
from dataclasses import asdict
from pathlib import Path

import click
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.squash import execute_squash
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.types import SquashError


@click.command(name="idempotent-squash")
def idempotent_squash() -> None:
    """Squash commits on current branch (idempotent - skips if already single commit)."""
    ops = RealGtKit()
    cwd = Path.cwd()
    result = render_events(execute_squash(ops, cwd))
    click.echo(json.dumps(asdict(result), indent=2))
    if isinstance(result, SquashError):
        raise SystemExit(1)
