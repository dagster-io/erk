"""Machine adapter for workflow run list."""

import click

from erk.cli.commands.run.operation import (
    WorkflowRunListRequest,
    WorkflowRunListResult,
    run_workflow_run_list,
)
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.agentclick.mcp_exposed import mcp_exposed


@mcp_exposed(
    name="workflow_run_list",
    description=(
        "List recent GitHub Actions workflow runs for the current repository."
        " Returns run IDs, statuses, conclusions, workflow names, timestamps, and URLs."
    ),
)
@machine_command(
    request_type=WorkflowRunListRequest,
    output_types=(WorkflowRunListResult,),
)
@click.command("list")
@click.pass_obj
def json_workflow_run_list(
    ctx: ErkContext,
    *,
    request: WorkflowRunListRequest,
) -> WorkflowRunListResult | MachineCommandError:
    """List workflow runs as structured JSON."""
    return run_workflow_run_list(ctx, request)
