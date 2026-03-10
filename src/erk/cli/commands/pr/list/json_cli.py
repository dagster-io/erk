"""Machine adapter for pr list.

Accepts JSON from stdin, delegates to run_pr_list operation,
returns structured JSON output.
"""

import click

from erk.cli.commands.pr.list.operation import PrListRequest, PrListResult, run_pr_list
from erk.cli.repo_resolution import resolve_owner_repo
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.agentclick.mcp_exposed import mcp_exposed
from erk_shared.gateway.github.types import GitHubRepoId


@mcp_exposed(
    name="pr_list",
    description=(
        "List erk plans with status, labels, and metadata."
        " Returns JSON array of plans."
        " Use state parameter to filter by 'open' or 'closed'."
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
    """List plans as structured JSON."""
    owner, repo_name = resolve_owner_repo(ctx, target_repo=None)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    return run_pr_list(ctx, request, repo_id=repo_id)
