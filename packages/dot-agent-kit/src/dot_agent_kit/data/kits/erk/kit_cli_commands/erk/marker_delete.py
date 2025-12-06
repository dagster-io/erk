"""Delete a marker from the current worktree.

Usage:
    dot-agent run erk marker-delete pending-extraction

Exit Codes:
    0: Success (marker deleted or didn't exist)
    1: Error
"""

import json
from pathlib import Path

import click

from erk.core.markers import delete_marker, marker_exists


@click.command(name="marker-delete")
@click.argument("marker_name")
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
def marker_delete(marker_name: str, output_json: bool) -> None:
    """Delete a marker from the current worktree."""
    worktree_path = Path.cwd()
    existed = marker_exists(worktree_path, marker_name)
    delete_marker(worktree_path, marker_name)

    if output_json:
        click.echo(json.dumps({"deleted": existed, "marker": marker_name}))
    else:
        if existed:
            click.echo(f"Deleted marker: {marker_name}")
        else:
            click.echo(f"Marker did not exist: {marker_name}")
