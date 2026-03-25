"""Machine adapter for one-shot dispatch.

Accepts JSON from stdin, delegates to run_one_shot operation,
returns structured JSON output.
"""

import click

from erk.cli.commands.one_shot.operation import (
    OneShotRequest,
    run_one_shot,
)
from erk.cli.commands.one_shot_remote_dispatch import (
    OneShotDispatchResult,
    OneShotDryRunResult,
)
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.agentclick.mcp_exposed import mcp_exposed


@mcp_exposed(
    name="one_shot",
    description=(
        "Submit a task for fully autonomous remote execution.\n\n"
        "Returns JSON with 'success' field. On success: pr_number, pr_url, "
        "run_url, branch_name. With dry_run: preview without executing. "
        "On error: error_type and message."
    ),
)
@machine_command(
    request_type=OneShotRequest,
    output_types=(OneShotDispatchResult, OneShotDryRunResult),
)
@click.command("one-shot")
@click.pass_obj
def json_one_shot(
    ctx: ErkContext,
    *,
    request: OneShotRequest,
) -> OneShotDispatchResult | OneShotDryRunResult | MachineCommandError:
    """Submit a task for fully autonomous remote execution (JSON)."""
    return run_one_shot(ctx, request)
