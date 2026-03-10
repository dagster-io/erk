"""Machine adapter for pr dispatch.

Accepts JSON from stdin, delegates to run_pr_dispatch operation,
returns structured JSON output.
"""

import click

from erk.cli.commands.pr.dispatch.operation import (
    PrDispatchRequest,
    PrDispatchResult,
    run_pr_dispatch,
)
from erk.cli.repo_resolution import resolve_owner_repo
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command


@machine_command(
    request_type=PrDispatchRequest,
    output_types=(PrDispatchResult,),
)
@click.command("dispatch")
@click.pass_obj
def json_pr_dispatch(
    ctx: ErkContext,
    *,
    request: PrDispatchRequest,
) -> PrDispatchResult | MachineCommandError:
    """Dispatch a plan PR for remote AI implementation."""
    owner, repo_name = resolve_owner_repo(ctx, target_repo=None)
    return run_pr_dispatch(ctx, request, owner=owner, repo_name=repo_name)
