"""Machine adapter for objective check.

Accepts JSON from stdin, delegates to run_objective_check operation,
returns structured JSON output.
"""

import click

from erk.cli.commands.objective.check.operation import (
    ObjectiveCheckRequest,
    ObjectiveCheckResult,
    run_objective_check,
)
from erk.cli.repo_resolution import resolve_owner_repo
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.gateway.github.types import GitHubRepoId


@machine_command(
    request_type=ObjectiveCheckRequest,
    output_types=(ObjectiveCheckResult,),
)
@click.command("check")
@click.pass_obj
def json_objective_check(
    ctx: ErkContext,
    *,
    request: ObjectiveCheckRequest,
) -> ObjectiveCheckResult | MachineCommandError:
    """Validate an objective's format and roadmap as structured JSON."""
    owner, repo_name = resolve_owner_repo(ctx, target_repo=None)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    return run_objective_check(ctx, request, repo_id=repo_id)
