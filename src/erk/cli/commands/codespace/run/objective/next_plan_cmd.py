"""Run objective next-plan remotely on a codespace."""

import click

from erk.cli.commands.codespace.resolve import resolve_codespace
from erk.core.codespace_run import build_codespace_ssh_command
from erk.core.context import ErkContext


@click.command("next-plan")
@click.argument("issue_ref")
@click.option("--codespace", "-c", "name", default=None, help="Codespace name.")
@click.pass_obj
def run_next_plan(ctx: ErkContext, issue_ref: str, name: str | None) -> None:
    """Run objective next-plan remotely on a codespace.

    ISSUE_REF is an objective issue number or GitHub URL.

    Starts the codespace if stopped, then executes 'erk objective next-plan'
    via SSH, streaming output to the terminal.
    """
    codespace = resolve_codespace(ctx.codespace_registry, name)

    click.echo(f"Starting codespace '{codespace.name}'...", err=True)
    ctx.codespace.start_codespace(codespace.gh_name)

    remote_cmd = build_codespace_ssh_command(f"erk objective next-plan {issue_ref}")
    click.echo(
        f"Running 'erk objective next-plan {issue_ref}' on '{codespace.name}'...",
        err=True,
    )
    ctx.codespace.exec_ssh_interactive(codespace.gh_name, remote_cmd)
