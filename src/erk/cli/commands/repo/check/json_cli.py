"""Machine adapter for repo check.

Accepts JSON from stdin, delegates to run_repo_check operation,
returns structured JSON output.
"""

import click

from erk.cli.commands.repo.check.operation import (
    RepoCheckRequest,
    RepoCheckResult,
    run_repo_check,
)
from erk_shared.agentclick.machine_command import MachineCommandError, machine_command
from erk_shared.agentclick.mcp_exposed import mcp_exposed


@mcp_exposed(
    name="repo_check",
    description=(
        "Validate that a remote GitHub repo has all required workflows,"
        " secrets, variables, permissions, and labels for erk automation."
    ),
)
@machine_command(
    request_type=RepoCheckRequest,
    output_types=(RepoCheckResult,),
)
@click.command("check")
def json_repo_check(
    *,
    request: RepoCheckRequest,
) -> RepoCheckResult | MachineCommandError:
    """Validate remote repo setup as structured JSON."""
    return run_repo_check(request)
