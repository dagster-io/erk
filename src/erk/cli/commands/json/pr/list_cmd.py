"""Machine adapter for pr list command: erk json pr list."""

import click

from erk.cli.commands.pr.list_cmd import PrListResult
from erk.cli.commands.pr.list_operation import PrListRequest, run_pr_list
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import machine_command


@machine_command(
    request_type=PrListRequest,
    result_types=(PrListResult,),
    name="pr_list",
    description=(
        "List erk plans with status, labels, and metadata."
        " Returns JSON array of plans."
        " Use state parameter to filter by 'open' or 'closed'."
    ),
)
@click.command("list")
@click.pass_obj
def json_pr_list(
    ctx: ErkContext,
    *,
    request: PrListRequest,
) -> PrListResult:
    """Machine-readable pr list."""
    return run_pr_list(request, ctx=ctx)
