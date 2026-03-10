"""Machine-facing `erk json pr view` command."""

from __future__ import annotations

import click

from erk.cli.commands.pr.view_operation import PrViewRequest, PrViewResult, run_pr_view
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import (
    MachineCommandError,
    machine_command,
)
from erk_shared.agentclick.mcp_exposed import mcp_exposed


@mcp_exposed(
    name="pr_view",
    description=(
        "View a specific plan's metadata, header info, and body content."
        " Returns plan title, state, labels, timestamps, and header metadata."
    ),
)
@machine_command(
    request_type=PrViewRequest,
    output_types=(PrViewResult,),
)
@click.command("view")
@click.pass_obj
def json_pr_view(
    ctx: ErkContext,
    *,
    request: PrViewRequest,
) -> PrViewResult | MachineCommandError:
    """View a single plan from stdin JSON."""

    return run_pr_view(request, ctx=ctx)
