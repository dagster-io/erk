"""Graphite update-pr CLI command."""

import json
import sys
from pathlib import Path

import click
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.update_pr import execute_update_pr
from erk_shared.integrations.gt.real import RealGtKit


@click.command()
def pr_update() -> None:
    """Graphite update-pr workflow.

    Usage:
        dot-agent run gt pr-update
    """
    ops = RealGtKit()
    cwd = Path.cwd()
    result = render_events(execute_update_pr(ops, cwd))
    print(json.dumps(result))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    pr_update()
