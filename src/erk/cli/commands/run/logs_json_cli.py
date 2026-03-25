"""Machine adapter for workflow run logs."""

import click

from erk.cli.commands.run.operation import (
    WorkflowRunLogsRequest,
    WorkflowRunLogsResult,
    run_workflow_run_logs,
)
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.agentclick.mcp_exposed import mcp_exposed


@mcp_exposed(
    name="workflow_run_logs",
    description=(
        "Fetch the raw logs for a GitHub Actions workflow run."
        " Returns the run ID and full log text."
    ),
)
@machine_command(
    request_type=WorkflowRunLogsRequest,
    output_types=(WorkflowRunLogsResult,),
)
@click.command("logs")
@click.pass_obj
def json_workflow_run_logs(
    ctx: ErkContext,
    *,
    request: WorkflowRunLogsRequest,
) -> WorkflowRunLogsResult | MachineCommandError:
    """Fetch workflow run logs as structured JSON."""
    return run_workflow_run_logs(ctx, request)
