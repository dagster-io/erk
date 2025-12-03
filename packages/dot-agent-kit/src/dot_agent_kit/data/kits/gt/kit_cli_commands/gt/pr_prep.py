"""Prepare branch for PR submission CLI command."""

import json
from dataclasses import asdict
from pathlib import Path

import click
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.prep import execute_prep
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.types import PrepError


@click.command()
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID for scratch file isolation. "
    "Writes diff to .tmp/<session-id>/ in repo root.",
)
def pr_prep(session_id: str) -> None:
    """Prepare branch for PR submission (squash + diff extraction, no submit).

    Returns JSON with diff file path for AI commit message generation.
    """
    try:
        ops = RealGtKit()
        cwd = Path.cwd()
        result = render_events(execute_prep(ops, cwd, session_id))
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, PrepError):
            raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        raise SystemExit(130) from None
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise SystemExit(1) from None
