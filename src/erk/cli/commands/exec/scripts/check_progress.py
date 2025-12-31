"""Validate progress.md schema and structure.

This exec command validates that progress.md has valid YAML frontmatter
with required fields (steps, total_steps, completed_steps) and internal consistency.

Usage:
    erk exec check-progress
    erk exec check-progress --json

Output:
    JSON with validation status and errors (--json mode)
    Human-readable validation result (normal mode)

Exit Codes:
    0: Valid
    1: Invalid or missing

Examples:
    $ erk exec check-progress --json
    {"valid": true, "errors": []}

    $ erk exec check-progress --json
    {"valid": false, "errors": ["Missing 'steps' field"]}

    $ erk exec check-progress
    progress.md schema is valid
"""

import json

import click

from erk_shared.context.helpers import require_cwd
from erk_shared.impl_folder import validate_progress_schema


@click.command(name="check-progress")
@click.option("--json", "output_json", is_flag=True, help="Output JSON result")
@click.pass_context
def check_progress(ctx: click.Context, output_json: bool) -> None:
    """Validate progress.md has valid YAML frontmatter with required fields.

    Checks that progress.md exists in .impl/ directory and validates:
    - YAML frontmatter parses correctly
    - Required fields exist: steps, total_steps, completed_steps
    - Each step has text and completed fields
    - Consistency: total_steps matches len(steps), completed_steps matches actual count
    """
    cwd = require_cwd(ctx)
    progress_file = cwd / ".impl" / "progress.md"

    errors = validate_progress_schema(progress_file)

    if output_json:
        result = {"valid": len(errors) == 0, "errors": errors}
        click.echo(json.dumps(result))
        if errors:
            raise SystemExit(1)
        return

    if errors:
        for e in errors:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    click.echo("progress.md schema is valid")
