"""Machine adapter for workflow run status."""

import click

from erk.cli.commands.run.operation import (
    WorkflowRunStatusRequest,
    WorkflowRunStatusResult,
    run_workflow_run_status,
)
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.agentclick.mcp_exposed import mcp_exposed


@mcp_exposed(
    name="workflow_run_status",
    description=(
        "Get the current status for a GitHub Actions workflow run."
        " Returns state, conclusion, workflow name, timestamps, and URL."
    ),
)
@machine_command(
    request_type=WorkflowRunStatusRequest,
    output_types=(WorkflowRunStatusResult,),
)
@click.command("status")
@click.pass_obj
def json_workflow_run_status(
    ctx: ErkContext,
    *,
    request: WorkflowRunStatusRequest,
) -> WorkflowRunStatusResult | MachineCommandError:
    """Get workflow run status as structured JSON."""
    return run_workflow_run_status(ctx, request)
