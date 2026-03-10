"""Machine adapter for pr view command: erk json pr view."""

import click

from erk.cli.commands.pr.view_cmd import PrViewResult
from erk.cli.commands.pr.view_operation import PrViewRequest, run_pr_view
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import machine_command


@machine_command(
    request_type=PrViewRequest,
    result_types=(PrViewResult,),
    name="pr_view",
    description=(
        "View a specific plan's metadata, header info, and body content."
        " Returns plan title, state, labels, timestamps, and header metadata."
    ),
)
@click.command("view")
@click.pass_obj
def json_pr_view(
    ctx: ErkContext,
    *,
    request: PrViewRequest,
) -> PrViewResult:
    """Machine-readable pr view."""
    return run_pr_view(request, ctx=ctx)
