"""Machine adapter for pr view.

Accepts JSON from stdin, delegates to run_pr_view operation,
returns structured JSON output.
"""

import click

from erk.cli.commands.pr.view.operation import PrViewRequest, PrViewResult, run_pr_view
from erk.cli.repo_resolution import resolve_owner_repo
from erk.core.context import ErkContext
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.agentclick.mcp_exposed import mcp_exposed
from erk_shared.gateway.github.types import GitHubRepoId


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
    """View a plan's metadata as structured JSON."""
    owner, repo_name = resolve_owner_repo(ctx, target_repo=None)
    repo_id = GitHubRepoId(owner=owner, repo=repo_name)
    return run_pr_view(ctx, request, repo_id=repo_id)
