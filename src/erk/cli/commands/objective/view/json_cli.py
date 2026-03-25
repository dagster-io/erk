"""Machine adapter for objective view.

Accepts JSON from stdin, delegates to run_objective_view operation,
returns structured JSON output.
"""

import click

from erk.cli.commands.objective.view.operation import (
    ObjectiveViewRequest,
    ObjectiveViewResult,
    run_objective_view,
)
from erk.cli.repo_resolution import resolve_owner_repo
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.gateway.github.types import GitHubRepoId


@machine_command(
    request_type=ObjectiveViewRequest,
    output_types=(ObjectiveViewResult,),
)
@click.command("view")
@click.pass_obj
def json_objective_view(
    ctx: ErkContext,
    *,
    request: ObjectiveViewRequest,
) -> ObjectiveViewResult | MachineCommandError:
    """View an objective's roadmap as structured JSON."""
    owner, repo_name = resolve_owner_repo(ctx, target_repo=None)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    return run_objective_view(ctx, request, repo_id=repo_id)
