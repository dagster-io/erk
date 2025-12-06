"""Check if a marker exists in the current worktree.

Usage:
    dot-agent run erk marker-exists pending-extraction

Exit Codes:
    0: Marker exists
    1: Marker does not exist
"""

import json
from pathlib import Path

import click
from erk_shared.scratch.markers import marker_exists


@click.command(name="marker-exists")
@click.argument("marker_name")
@click.option("--json", "output_json", is_flag=True, help="Output JSON instead of exit code")
def marker_exists_cmd(marker_name: str, output_json: bool) -> None:
    """Check if a marker exists in the current worktree."""
    worktree_path = Path.cwd()
    exists = marker_exists(worktree_path, marker_name)

    if output_json:
        click.echo(json.dumps({"exists": exists, "marker": marker_name}))
    else:
        if exists:
            click.echo(f"Marker exists: {marker_name}")
        else:
            click.echo(f"Marker does not exist: {marker_name}")
            raise SystemExit(1)
