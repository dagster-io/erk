"""Update objective after landing a PR.

Standalone exec script that calls Claude to update the linked objective
after a PR has been merged. Always exits 0 (fail-open) because the
landing has already succeeded.

This is a thin wrapper around the shared helper in objective_helpers.py.
It remains available for manual retries via:
    erk exec objective-update-after-land --objective 42 --pr 123 --branch feature

Exit Codes:
    0: Always (fail-open - landing already succeeded)
"""

import click

from erk.cli.commands.objective_helpers import run_objective_update_after_land
from erk_shared.context.helpers import require_context


@click.command(name="objective-update-after-land")
@click.option(
    "--objective",
    type=int,
    required=True,
    help="Linked objective issue number",
)
@click.option(
    "--pr",
    type=int,
    required=True,
    help="PR number that was just landed",
)
@click.option(
    "--branch",
    required=True,
    help="Branch name that was landed",
)
@click.pass_context
def objective_update_after_land(
    ctx: click.Context,
    *,
    objective: int,
    pr: int,
    branch: str,
) -> None:
    """Update objective after landing a PR.

    Calls Claude to update the linked objective with the landed PR information.
    Always exits 0 (fail-open) because the landing has already succeeded.
    """
    erk_ctx = require_context(ctx)
    run_objective_update_after_land(erk_ctx, objective=objective, pr=pr, branch=branch)
