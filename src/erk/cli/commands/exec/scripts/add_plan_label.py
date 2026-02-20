"""Backend-aware label addition for plans.

Usage:
    erk exec add-plan-label <plan-number> --label <label>

Output:
    JSON with {success, plan_number, label}

Exit Codes:
    0: Success - label added
    1: Error - plan not found or API error
    2: Usage error - missing required --label flag
"""

import json

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root


@click.command(name="add-plan-label")
@click.argument("plan_number", type=int)
@click.option(
    "--label",
    required=True,
    help="Label to add to the plan",
)
@click.pass_context
def add_plan_label(
    ctx: click.Context,
    plan_number: int,
    *,
    label: str,
) -> None:
    """Add a label to a plan via the appropriate backend."""
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    plan_id = str(plan_number)

    try:
        backend.add_label(repo_root, plan_id, label)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to add label to plan #{plan_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "plan_number": plan_number,
                "label": label,
            }
        )
    )
