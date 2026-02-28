"""Restack command that auto-launches Claude on conflicts."""

import os
import subprocess

import click

from erk.cli.graphite_command import GraphiteCommand
from erk.core.context import ErkContext


@click.command("restack", cls=GraphiteCommand)
@click.pass_obj
def restack_stack(ctx: ErkContext) -> None:
    """Restack the current branch stack using Graphite.

    Runs ``gt restack`` and, if merge conflicts are detected,
    automatically launches Claude Code with ``/erk:fix-conflicts``.

    When already running inside Claude Code (CLAUDECODE env var set),
    prints a suggestion to run ``/erk:fix-conflicts`` instead of
    launching a nested session.
    """
    result = subprocess.run(
        ["gt", "restack", "--no-interactive"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        click.echo("Stack restacked successfully.", err=True)
        if result.stdout.strip():
            click.echo(result.stdout.strip(), err=True)
        return

    # Restack failed — check if there are merge conflicts
    status_result = subprocess.run(
        ["git", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    status_output = status_result.stdout

    has_conflicts = "rebase in progress" in status_output or "Unmerged paths" in status_output

    if not has_conflicts:
        click.echo("gt restack failed:", err=True)
        if result.stderr.strip():
            click.echo(result.stderr.strip(), err=True)
        if result.stdout.strip():
            click.echo(result.stdout.strip(), err=True)
        raise SystemExit(1)

    # Conflicts detected
    if "CLAUDECODE" in os.environ:
        click.echo("Merge conflicts detected during restack.", err=True)
        click.echo("Run /erk:fix-conflicts to resolve them.", err=True)
        raise SystemExit(1)

    click.echo("Conflicts detected, launching Claude to fix them...", err=True)
    os.execvp("claude", ["claude", "/erk:fix-conflicts"])
