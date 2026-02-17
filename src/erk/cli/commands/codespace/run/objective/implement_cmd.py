"""Run objective implement remotely on a codespace."""

import click

from erk.cli.commands.codespace.resolve import resolve_codespace
from erk.core.codespace_run import build_codespace_ssh_command
from erk.core.context import ErkContext


@click.command("implement")
@click.argument("issue_ref")
@click.option("--codespace", "-c", "name", default=None, help="Codespace name.")
@click.option(
    "-d",
    "--dangerous",
    is_flag=True,
    default=False,
    help="Allow dangerous permissions by passing --allow-dangerously-skip-permissions to Claude",
)
@click.pass_obj
def run_implement(ctx: ErkContext, issue_ref: str, name: str | None, dangerous: bool) -> None:
    """Run objective implement remotely on a codespace.

    ISSUE_REF is an objective issue number or GitHub URL.

    Starts the codespace if stopped, then executes 'erk objective implement'
    via SSH, streaming output to the terminal.
    """
    codespace = resolve_codespace(ctx.codespace_registry, name)

    click.echo(f"Starting codespace '{codespace.name}'...", err=True)
    ctx.codespace.start_codespace(codespace.gh_name)

    if dangerous:
        remote_erk_cmd = f"erk objective implement -d {issue_ref}"
    else:
        remote_erk_cmd = f"erk objective implement {issue_ref}"
    remote_cmd = build_codespace_ssh_command(remote_erk_cmd)
    click.echo(
        f"Running '{remote_erk_cmd}' on '{codespace.name}'...",
        err=True,
    )
    ctx.codespace.exec_ssh_interactive(codespace.gh_name, remote_cmd)
