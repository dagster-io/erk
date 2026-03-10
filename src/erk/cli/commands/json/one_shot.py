"""Machine adapter for one-shot command: erk json one-shot."""

import click

from erk.cli.commands.one_shot_operation import OneShotRequest, run_one_shot
from erk.cli.commands.one_shot_remote_dispatch import OneShotDispatchResult, OneShotDryRunResult
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import machine_command


@machine_command(
    request_type=OneShotRequest,
    result_types=(OneShotDispatchResult, OneShotDryRunResult),
    name="one_shot",
    description=(
        "Submit a task for fully autonomous remote execution.\n\n"
        "Returns JSON with 'success' field. On success: pr_number, pr_url, "
        "run_url, branch_name. With dry_run: preview without executing. "
        "On error: error_type and message."
    ),
)
@click.command("one-shot")
@click.pass_obj
def json_one_shot(
    ctx: ErkContext,
    *,
    request: OneShotRequest,
) -> OneShotDispatchResult | OneShotDryRunResult:
    """Machine-readable one-shot dispatch."""
    return run_one_shot(request, ctx=ctx)
