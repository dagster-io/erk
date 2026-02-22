"""Convert plan title to filename.

Usage:
    erk exec issue-title-to-filename "Plan Title"

Single source of truth for filename transformation for /erk:plan-save.

Output:
    Filename on stdout (e.g., "my-feature-plan.md")
    Error message on stderr with exit code 1 on failure

Exit Codes:
    0: Success
    1: Error (empty title)
    2: Validation failed (title rejected by validate_plan_title)
"""

import json

import click

from erk_shared.naming import InvalidPlanTitle, generate_filename_from_title, validate_plan_title


@click.command(name="issue-title-to-filename")
@click.argument("title")
def issue_title_to_filename(title: str) -> None:
    """Convert plan title to filename.

    TITLE: Plan title to convert
    """
    result = validate_plan_title(title)
    if isinstance(result, InvalidPlanTitle):
        click.echo(
            json.dumps(
                {
                    "error_type": result.error_type,
                    "agent_guidance": result.message,
                }
            ),
            err=True,
        )
        raise SystemExit(2)

    filename = generate_filename_from_title(title)
    click.echo(filename)
