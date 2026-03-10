"""Machine-facing `erk json pr list` command."""

from __future__ import annotations

import click

from erk.cli.commands.pr.list_operation import PrListRequest, PrListResult, run_pr_list
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import (
    MachineCommandError,
    machine_command,
)
from erk_shared.agentclick.mcp_exposed import mcp_exposed


@mcp_exposed(
    name="pr_list",
    description=(
        "List erk plans with status, labels, and metadata."
        " Returns JSON array of plans."
        " Use state to filter by 'open' or 'closed'."
    ),
)
@machine_command(
    request_type=PrListRequest,
    output_types=(PrListResult,),
)
@click.command("list")
@click.pass_obj
def json_pr_list(
    ctx: ErkContext,
    *,
    request: PrListRequest,
) -> PrListResult | MachineCommandError:
    """List plans from stdin JSON."""

    return run_pr_list(request, ctx=ctx)
