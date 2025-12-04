"""Idempotent squash CLI command.

Squash commits on current branch (idempotent - skips if already single commit).
"""

import json
from pathlib import Path

import click
from dot_agent_kit.cli.schema_formatting import json_output
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.squash import execute_squash
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.types import SquashError, SquashSuccess


@json_output(SquashSuccess | SquashError)
@click.command(name="idempotent-squash")
def idempotent_squash() -> None:
    """Squash commits on current branch (idempotent - skips if already single commit)."""
    ops = RealGtKit()
    cwd = Path.cwd()
    result = render_events(execute_squash(ops, cwd))
    click.echo(json.dumps(result, indent=2))
    if not result["success"]:
        raise SystemExit(1)
