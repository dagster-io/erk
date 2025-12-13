"""Land a single PR from worktree stack CLI command."""

import json
from dataclasses import asdict
from pathlib import Path

import click

from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.land_pr import execute_land_pr
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.types import LandPrError, LandPrSuccess


@click.command()
def land_pr() -> None:
    """Land a single PR from worktree stack without affecting upstack branches."""
    try:
        cwd = Path.cwd()
        ops = RealGtKit(cwd)
        result = render_events(execute_land_pr(ops, cwd))
        # Single line summary instead of formatted JSON
        if isinstance(result, LandPrSuccess):
            click.echo(f"✓ Merged PR #{result.pr_number} [{result.branch_name}]")
        else:
            click.echo(f"✗ Failed to merge: {result.message}")

        if isinstance(result, LandPrError):
            raise SystemExit(1)

    except Exception as e:
        error = LandPrError(
            success=False,
            error_type="merge_failed",
            message=f"Unexpected error: {e}",
            details={"error": str(e)},
        )
        click.echo(json.dumps(asdict(error), indent=2), err=True)
        raise SystemExit(1) from None
