"""Backend-aware label addition for plans.

Usage:
    erk exec add-plan-label <pr-number> --label <label>

Output:
    JSON with {success, pr_number, label}

Exit Codes:
    0: Success - label added
    1: Error - plan not found or API error
    2: Usage error - missing required --label flag
"""

import json

import click

from erk_shared.context.helpers import require_plan_backend, require_repo_root


@click.command(name="add-plan-label")
@click.argument("pr_number", type=int)
@click.option(
    "--label",
    required=True,
    help="Label to add to the PR",
)
@click.pass_context
def add_plan_label(
    ctx: click.Context,
    pr_number: int,
    *,
    label: str,
) -> None:
    """Add a label to a plan via the appropriate backend."""
    backend = require_plan_backend(ctx)
    repo_root = require_repo_root(ctx)

    pr_id = str(pr_number)

    try:
        backend.add_label(repo_root, pr_id, label)
    except RuntimeError as e:
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to add label to plan #{pr_number}: {e}",
                }
            )
        )
        raise SystemExit(1) from e

    click.echo(
        json.dumps(
            {
                "success": True,
                "pr_number": pr_number,
                "label": label,
            }
        )
    )
